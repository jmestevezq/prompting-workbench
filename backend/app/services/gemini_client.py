"""Gemini API client wrapper.

Structured to match ADK's internal behavior:
- Uses async API (client.aio.models.generate_content)
- Groups multiple function_calls into one Content(role="model")
- Groups multiple function_responses into one Content(role="user")
- Disables automatic_function_calling (manual loop control)
"""

import json
from typing import Any, Optional
from google import genai
from google.genai import types

from app.config import settings
from app.services.log_service import dev_log


def get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def build_tool_declarations(tool_definitions: list[dict]) -> Optional[types.Tool]:
    if not tool_definitions:
        return None
    function_declarations = []
    for tool_def in tool_definitions:
        fd = types.FunctionDeclaration(
            name=tool_def["name"],
            description=tool_def.get("description", ""),
            parameters=tool_def.get("parameters"),
        )
        function_declarations.append(fd)
    return types.Tool(function_declarations=function_declarations)


def build_contents(
    history: list[dict],
    user_message: Optional[str] = None,
) -> list[types.Content]:
    """Build Gemini-compatible contents from conversation history.

    Groups adjacent tool_call turns into a single Content(role="model")
    and adjacent tool_response turns into a single Content(role="user")
    to match ADK's content structure.
    """
    contents: list[types.Content] = []

    i = 0
    turns = list(history)
    while i < len(turns):
        turn = turns[i]
        role = turn["role"]

        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=turn["content"])]))
            i += 1

        elif role == "agent":
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=turn["content"])]))
            i += 1

        elif role == "tool_call":
            # Collect all consecutive tool_call turns into one Content(role="model")
            fc_parts = []
            while i < len(turns) and turns[i]["role"] == "tool_call":
                fc = turns[i].get("tool_call", {})
                fc_parts.append(types.Part.from_function_call(
                    name=fc.get("name", ""),
                    args=fc.get("args", {}),
                ))
                i += 1
            contents.append(types.Content(role="model", parts=fc_parts))

        elif role == "tool_response":
            # Collect all consecutive tool_response turns into one Content(role="user")
            fr_parts = []
            while i < len(turns) and turns[i]["role"] == "tool_response":
                fr = turns[i].get("tool_response", {})
                resp = fr.get("response", {})
                fr_parts.append(types.Part.from_function_response(
                    name=fr.get("name", ""),
                    response=resp if isinstance(resp, dict) else {"result": resp},
                ))
                i += 1
            contents.append(types.Content(role="user", parts=fr_parts))

        else:
            i += 1

    if user_message:
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    return contents


async def generate(
    system_prompt: str,
    model: str,
    contents: list[types.Content],
    tools: Optional[types.Tool] = None,
) -> dict:
    """Call Gemini and return structured result with raw request/response data.

    Uses the async API (client.aio) to avoid blocking the event loop,
    matching ADK's internal behavior.
    """
    client = get_client()

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    if tools:
        config.tools = [tools]

    raw_request = {
        "model": model,
        "system_instruction": system_prompt,
        "contents": _serialize_contents(contents),
        "tools": _serialize_tool(tools) if tools else None,
    }

    dev_log("GEMINI", "info", f"API call → {model}", {"turns": len(contents)})

    # Use async API to avoid blocking the event loop (matches ADK)
    response = await client.aio.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )

    # Extract function calls if present
    function_calls = []
    text_parts = []
    if response.candidates and response.candidates[0].content:
        for part in response.candidates[0].content.parts:
            if part.function_call:
                function_calls.append({
                    "name": part.function_call.name,
                    "args": dict(part.function_call.args) if part.function_call.args else {},
                })
            if part.text:
                text_parts.append(part.text)

    # Extract token usage
    token_usage = None
    if response.usage_metadata:
        token_usage = {
            "prompt_tokens": response.usage_metadata.prompt_token_count,
            "completion_tokens": response.usage_metadata.candidates_token_count,
            "total": response.usage_metadata.total_token_count,
        }

    raw_response = _serialize_response(response)

    fc_names = [fc["name"] for fc in function_calls] if function_calls else []
    dev_log("GEMINI", "info", f"API response ← {model}", {
        "function_calls": fc_names,
        "has_text": bool(text_parts),
        "token_usage": token_usage,
    })

    return {
        "response": response,
        "text": "\n".join(text_parts) if text_parts else None,
        "function_calls": function_calls,
        "raw_request": raw_request,
        "raw_response": raw_response,
        "token_usage": token_usage,
    }


def _serialize_contents(contents: list[types.Content]) -> list[dict]:
    result = []
    for content in contents:
        parts = []
        for part in content.parts:
            if part.text:
                parts.append({"text": part.text})
            elif part.function_call:
                parts.append({
                    "function_call": {
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args) if part.function_call.args else {},
                    }
                })
            elif part.function_response:
                parts.append({
                    "function_response": {
                        "name": part.function_response.name,
                        "response": part.function_response.response,
                    }
                })
        result.append({"role": content.role, "parts": parts})
    return result


def _serialize_schema(schema) -> Optional[dict]:
    """Convert a Gemini SDK Schema object to a plain dict."""
    if schema is None:
        return None
    if isinstance(schema, dict):
        return schema
    if hasattr(schema, 'model_dump'):
        return schema.model_dump(exclude_none=True)
    if hasattr(schema, 'to_dict'):
        return schema.to_dict()
    result: dict[str, Any] = {}
    if hasattr(schema, 'type') and schema.type:
        result["type"] = str(schema.type)
    if hasattr(schema, 'properties') and schema.properties:
        result["properties"] = {
            k: _serialize_schema(v) for k, v in schema.properties.items()
        }
    if hasattr(schema, 'required') and schema.required:
        result["required"] = list(schema.required)
    if hasattr(schema, 'description') and schema.description:
        result["description"] = schema.description
    if hasattr(schema, 'items') and schema.items:
        result["items"] = _serialize_schema(schema.items)
    return result if result else None


def _serialize_tool(tool: types.Tool) -> list[dict]:
    if not tool or not tool.function_declarations:
        return []
    result = []
    for fd in tool.function_declarations:
        result.append({
            "name": fd.name,
            "description": fd.description,
            "parameters": _serialize_schema(fd.parameters),
        })
    return result


def _serialize_response(response) -> dict:
    try:
        if hasattr(response, 'to_dict'):
            return response.to_dict()
        result = {}
        if response.candidates:
            result["candidates"] = []
            for candidate in response.candidates:
                c = {"content": {"parts": []}}
                if candidate.content:
                    for part in candidate.content.parts:
                        if part.text:
                            c["content"]["parts"].append({"text": part.text})
                        elif part.function_call:
                            c["content"]["parts"].append({
                                "function_call": {
                                    "name": part.function_call.name,
                                    "args": dict(part.function_call.args) if part.function_call.args else {},
                                }
                            })
                result["candidates"].append(c)
        if response.usage_metadata:
            result["usage_metadata"] = {
                "prompt_token_count": response.usage_metadata.prompt_token_count,
                "candidates_token_count": response.usage_metadata.candidates_token_count,
                "total_token_count": response.usage_metadata.total_token_count,
            }
        return result
    except Exception:
        return {"error": "Could not serialize response"}
