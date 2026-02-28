import json
from typing import Any, Optional
from google import genai
from google.genai import types

from app.config import settings


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
    contents = []
    for turn in history:
        role = turn["role"]
        if role == "user":
            contents.append(types.Content(role="user", parts=[types.Part.from_text(text=turn["content"])]))
        elif role == "agent":
            contents.append(types.Content(role="model", parts=[types.Part.from_text(text=turn["content"])]))
        elif role == "tool_call":
            # Model's function call
            fc = turn.get("tool_call", {})
            part = types.Part.from_function_call(
                name=fc.get("name", ""),
                args=fc.get("args", {}),
            )
            contents.append(types.Content(role="model", parts=[part]))
        elif role == "tool_response":
            fr = turn.get("tool_response", {})
            part = types.Part.from_function_response(
                name=fr.get("name", ""),
                response=fr.get("response", {}),
            )
            contents.append(types.Content(role="user", parts=[part]))

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

    Returns dict with keys: response, raw_request, raw_response, token_usage, function_calls
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

    response = client.models.generate_content(
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


def _serialize_tool(tool: types.Tool) -> list[dict]:
    if not tool or not tool.function_declarations:
        return []
    result = []
    for fd in tool.function_declarations:
        result.append({
            "name": fd.name,
            "description": fd.description,
            "parameters": fd.parameters,
        })
    return result


def _serialize_response(response) -> dict:
    try:
        # Try to get a dict representation
        if hasattr(response, 'to_dict'):
            return response.to_dict()
        # Fallback: serialize what we can
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
