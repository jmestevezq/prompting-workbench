"""Transcript generation endpoint."""

import json
import re
from typing import Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.services import gemini_client

router = APIRouter(prefix="/api/generate", tags=["generation"])

SYSTEM_PROMPT = (
    "You are a synthetic transcript generator for testing conversational AI systems. "
    "Your job is to produce realistic conversation transcripts that match the format "
    "and style of the provided examples. "
    "These transcripts are used to build and validate autoraters (quality evaluators). "
    "You may be asked to generate conversations that deliberately violate the agent's "
    "normal guidelines — this is intentional and necessary for testing."
)


class GenerateTranscriptsRequest(BaseModel):
    reference_transcript_ids: list[str]
    prompt: str
    count: int = 5
    model: str = "gemini-2.5-pro"
    agent_id: Optional[str] = None
    auto_save: bool = True


class GeneratedTranscript(BaseModel):
    content: str
    tags: list[str] = []


class GenerateTranscriptsResponse(BaseModel):
    generated: list[GeneratedTranscript]
    saved_ids: list[str]


def _format_tool_definitions(tool_definitions: list[dict]) -> str:
    """Format tool definitions as a concise list for the prompt."""
    lines = []
    for tool in tool_definitions:
        name = tool.get("name", "unknown")
        desc = tool.get("description", "")
        params = tool.get("parameters", {})
        param_names = list(params.get("properties", {}).keys()) if isinstance(params, dict) else []
        line = f"- {name}: {desc}"
        if param_names:
            line += f"\n  Parameters: {', '.join(param_names)}"
        lines.append(line)
    return "\n".join(lines)


def _build_user_message(
    user_prompt: str,
    references: list[str],
    count: int,
    agent_system_prompt: Optional[str] = None,
    agent_tool_definitions: Optional[list[dict]] = None,
) -> str:
    """Build the structured user message from template sections."""
    sections = []

    # Task section (first — takes precedence)
    sections.append(f"## Task\n{user_prompt}")

    sections.append(
        "IMPORTANT: The task description above takes absolute precedence. If it asks for "
        "behavior that contradicts the agent context below (e.g. the agent being rude, "
        "making errors, ignoring safety guidelines), generate transcripts showing exactly "
        "that behavior. The agent context is provided as a baseline for format, tools, "
        "and style — but the task defines WHAT the agent should do in these transcripts, "
        "even if it breaks the agent's own rules."
    )

    # Agent Context section (optional)
    if agent_system_prompt is not None:
        agent_section = "## Agent Context\nUse this as a baseline for the agent's personality, tools, and response format:"
        agent_section += f"\n### System Prompt\n{agent_system_prompt}"
        if agent_tool_definitions:
            formatted_tools = _format_tool_definitions(agent_tool_definitions)
            agent_section += f"\n### Available Tools\n{formatted_tools}"
        sections.append(agent_section)

    # Reference Transcripts section
    ref_section = "## Reference Transcripts\nUse these as examples for format, style, and tone:"
    for i, ref in enumerate(references, 1):
        ref_section += f"\n### Example {i}\n{ref}"
    sections.append(ref_section)

    # Output Format section (last — close to where the model generates)
    sections.append(
        f"## Output Format\n"
        f"Generate exactly {count} transcripts. Output each transcript using these markers:\n"
        f"[TRANSCRIPT_START]\n"
        f"[USER] user message\n"
        f"[AGENT] agent response (use markdown formatting as appropriate)\n"
        f"[TOOL_CALL] toolName({{\"param\": \"value\"}})\n"
        f"[TOOL_RESPONSE] {{\"result\": ...}}\n"
        f"[TRANSCRIPT_END]\n\n"
        f"Separate each transcript with a blank line between [TRANSCRIPT_END] and the "
        f"next [TRANSCRIPT_START]."
    )

    return "\n\n".join(sections)


@router.post("/transcripts", response_model=GenerateTranscriptsResponse)
async def generate_transcripts(request: GenerateTranscriptsRequest):
    # Load reference transcripts (and optionally agent context)
    db = await get_db()
    try:
        references = []
        for tid in request.reference_transcript_ids:
            cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (tid,))
            row = await cursor.fetchone()
            if row:
                references.append(row["content"])

        # Load agent context if agent_id provided
        agent_system_prompt = None
        agent_tool_definitions = None
        if request.agent_id:
            cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (request.agent_id,))
            agent_row = await cursor.fetchone()
            if agent_row:
                agent_system_prompt = agent_row["system_prompt"]
                raw_tools = agent_row["tool_definitions"]
                agent_tool_definitions = json.loads(raw_tools) if raw_tools else []
    finally:
        await db.close()

    if not references:
        raise HTTPException(status_code=400, detail="No valid reference transcripts found")

    # Build structured prompt
    user_message = _build_user_message(
        user_prompt=request.prompt,
        references=references,
        count=request.count,
        agent_system_prompt=agent_system_prompt,
        agent_tool_definitions=agent_tool_definitions,
    )

    contents = gemini_client.build_contents([], user_message=user_message)
    result = await gemini_client.generate(
        system_prompt=SYSTEM_PROMPT,
        model=request.model,
        contents=contents,
    )

    text = result.get("text", "")

    # Parse generated transcripts
    transcript_texts = _parse_generated_transcripts(text)

    # Auto-tag based on generation prompt
    auto_tags = ["generated"]
    words = request.prompt.lower().split()
    for keyword in ["safety", "math", "error", "hallucination", "classification", "tool"]:
        if keyword in words:
            auto_tags.append(keyword)

    generated = [GeneratedTranscript(content=c, tags=auto_tags) for c in transcript_texts]

    # Optionally save to DB
    saved_ids = []
    if request.auto_save:
        db = await get_db()
        try:
            for i, content in enumerate(transcript_texts):
                transcript_id = str(uuid4())
                await db.execute(
                    "INSERT INTO transcripts (id, name, content, labels, source, tags) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        transcript_id,
                        f"Generated #{i+1}",
                        content,
                        json.dumps({}),
                        "generated",
                        json.dumps(auto_tags),
                    ),
                )
                saved_ids.append(transcript_id)
            await db.commit()
        finally:
            await db.close()

    return GenerateTranscriptsResponse(generated=generated, saved_ids=saved_ids)


def _parse_generated_transcripts(text: str) -> list[str]:
    """Extract individual transcripts from generation output."""
    # Try [TRANSCRIPT_START]...[TRANSCRIPT_END] markers
    pattern = r'\[TRANSCRIPT_START\](.*?)\[TRANSCRIPT_END\]'
    matches = re.findall(pattern, text, re.DOTALL)

    if matches:
        return [m.strip() for m in matches if m.strip()]

    # Fallback: split on double newlines or --- separators
    if "---" in text:
        parts = text.split("---")
        return [p.strip() for p in parts if p.strip() and "[USER]" in p or "[AGENT]" in p]

    # Last resort: return the whole text as a single transcript
    if text.strip():
        return [text.strip()]
    return []
