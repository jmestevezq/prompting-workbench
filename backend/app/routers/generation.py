"""Transcript generation endpoint."""

import json
import re
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import get_db
from app.services import gemini_client

router = APIRouter(prefix="/api/generate", tags=["generation"])


class GenerateTranscriptsRequest(BaseModel):
    reference_transcript_ids: list[str]
    prompt: str
    count: int = 5
    model: str = "gemini-2.5-pro"


class GeneratedTranscript(BaseModel):
    content: str
    tags: list[str] = []


class GenerateTranscriptsResponse(BaseModel):
    generated: list[GeneratedTranscript]
    saved_ids: list[str]


@router.post("/transcripts", response_model=GenerateTranscriptsResponse)
async def generate_transcripts(request: GenerateTranscriptsRequest):
    # Load reference transcripts
    db = await get_db()
    try:
        references = []
        for tid in request.reference_transcript_ids:
            cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (tid,))
            row = await cursor.fetchone()
            if row:
                references.append(row["content"])
    finally:
        await db.close()

    if not references:
        raise HTTPException(status_code=400, detail="No valid reference transcripts found")

    # Build generation prompt
    ref_text = "\n\n---\n\n".join(references)
    meta_prompt = f"""You are generating synthetic conversation transcripts for testing.

Here are reference transcripts showing the format and style:
{ref_text}

Generate {request.count} transcripts with the following characteristics:
{request.prompt}

Output each transcript in this format:
[TRANSCRIPT_START]
[USER] ...
[AGENT] ...
[TOOL_CALL] ...
[TOOL_RESPONSE] ...
[AGENT] ...
[TRANSCRIPT_END]"""

    contents = gemini_client.build_contents([], user_message=meta_prompt)
    result = await gemini_client.generate(
        system_prompt="You are a transcript generator. Generate realistic conversation transcripts.",
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

    # Save to DB
    saved_ids = []
    generated = []
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
            generated.append(GeneratedTranscript(content=content, tags=auto_tags))
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
