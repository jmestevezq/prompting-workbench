"""Core agent loop: prompt building, Gemini calling, tool execution, debug capture.

Matches ADK's internal behavior:
- Multiple function_calls grouped into one Content(role="model", parts=[fc1, fc2, ...])
- All function_responses grouped into one Content(role="user", parts=[fr1, fr2, ...])
- Tool calls executed in parallel via asyncio.gather (like ADK's handle_function_calls_async)
- Async Gemini API calls (non-blocking)
"""

import asyncio
import json
from uuid import uuid4
from typing import Any, AsyncGenerator
from google.genai import types

from app.database import get_db
from app.services import gemini_client
from app.services.mock_tools import execute_tool


class SessionState:
    """In-memory state for an active chat session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agent_config: dict | None = None
        self.fixtures: dict = {}  # {"user_profile": {...}, "transactions": [...]}
        self.fixture_ids: list[str] = []
        self.tool_overrides: dict = {}  # {"tool_name": {"data": ..., "active": True}}
        self.conversation_history: list[dict] = []  # List of turn dicts

    async def load(self):
        """Load session, agent, and fixture data from DB."""
        db = await get_db()
        try:
            cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (self.session_id,))
            session = await cursor.fetchone()
            if not session:
                raise ValueError(f"Session {self.session_id} not found")

            # Load agent config
            cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (session["agent_id"],))
            agent = await cursor.fetchone()
            if not agent:
                raise ValueError(f"Agent {session['agent_id']} not found")

            self.agent_config = {
                "id": agent["id"],
                "name": agent["name"],
                "system_prompt": agent["system_prompt"],
                "model": agent["model"],
                "tool_definitions": json.loads(agent["tool_definitions"]) if agent["tool_definitions"] else [],
            }

            # If agent has an active version, use its system_prompt and tool_details
            active_version_id = None
            try:
                active_version_id = agent["active_version_id"]
            except (IndexError, KeyError):
                pass

            if active_version_id:
                cursor = await db.execute(
                    "SELECT * FROM agent_versions WHERE id = ?", (active_version_id,)
                )
                version = await cursor.fetchone()
                if version:
                    self.agent_config["system_prompt"] = version["system_prompt"]
                    if version["tool_details"]:
                        tool_details = json.loads(version["tool_details"])
                        if tool_details:
                            self.agent_config["tool_details"] = tool_details

            # Load fixtures
            self.fixture_ids = json.loads(session["fixture_ids"]) if session["fixture_ids"] else []
            await self._load_fixtures(db)

            # Load existing conversation turns
            cursor = await db.execute(
                "SELECT * FROM turns WHERE session_id = ? AND is_active = 1 ORDER BY turn_index ASC",
                (self.session_id,),
            )
            rows = await cursor.fetchall()
            self.conversation_history = []
            for row in rows:
                turn = {
                    "id": row["id"],
                    "role": row["role"],
                    "content": row["content"],
                }
                if row["tool_calls"]:
                    tc = json.loads(row["tool_calls"])
                    if tc:
                        turn["tool_call"] = tc[0] if isinstance(tc, list) else tc
                if row["tool_responses"]:
                    tr = json.loads(row["tool_responses"])
                    if tr:
                        turn["tool_response"] = tr[0] if isinstance(tr, list) else tr
                self.conversation_history.append(turn)
        finally:
            await db.close()

    async def _load_fixtures(self, db):
        """Load fixture data into memory by type."""
        self.fixtures = {}
        for fid in self.fixture_ids:
            cursor = await db.execute("SELECT * FROM fixtures WHERE id = ?", (fid,))
            fixture = await cursor.fetchone()
            if fixture:
                fixture_type = fixture["type"]
                data = json.loads(fixture["data"]) if fixture["data"] else None
                self.fixtures[fixture_type] = data

    async def swap_fixtures(self, new_fixture_ids: list[str]):
        """Swap active fixtures mid-conversation."""
        self.fixture_ids = new_fixture_ids
        db = await get_db()
        try:
            await db.execute(
                "UPDATE sessions SET fixture_ids = ? WHERE id = ?",
                (json.dumps(new_fixture_ids), self.session_id),
            )
            await db.commit()
            await self._load_fixtures(db)
        finally:
            await db.close()


def _execute_tool_call(
    tool_name: str,
    tool_args: dict,
    state: SessionState,
    tool_response_overrides: dict | None,
) -> Any:
    """Execute a single tool call, checking overrides first (like ADK's tool dispatch)."""
    if tool_response_overrides and tool_name in tool_response_overrides:
        return tool_response_overrides[tool_name]
    if state.tool_overrides.get(tool_name, {}).get("active"):
        return state.tool_overrides[tool_name]["data"]
    return execute_tool(tool_name, tool_args, state.fixtures)


async def run_agent_turn(
    state: SessionState,
    user_message: str | None = None,
    system_prompt_override: str | None = None,
    tool_response_overrides: dict | None = None,
    modified_history: list[dict] | None = None,
) -> AsyncGenerator[dict, None]:
    """Execute one agent turn: call Gemini, handle tool calls, yield streaming events.

    Matches ADK's agent loop:
    - Groups multiple function_calls into one Content(role="model")
    - Executes tools in parallel via asyncio
    - Groups all function_responses into one Content(role="user")
    - Loops until Gemini returns a text response
    """
    if not state.agent_config:
        yield {"type": "error", "message": "Session not loaded"}
        return

    system_prompt = system_prompt_override or state.agent_config["system_prompt"]
    model = state.agent_config["model"]
    tool_defs = state.agent_config["tool_definitions"]

    # Build conversation history
    history = modified_history if modified_history is not None else list(state.conversation_history)

    # Save user turn if this is a new message (not a rerun)
    if user_message:
        user_turn_id = str(uuid4())
        turn_index = len(history)
        history.append({"role": "user", "content": user_message})

        db = await get_db()
        try:
            await db.execute(
                "INSERT INTO turns (id, session_id, turn_index, role, content) VALUES (?, ?, ?, ?, ?)",
                (user_turn_id, state.session_id, turn_index, "user", user_message),
            )
            await db.commit()
        finally:
            await db.close()

        state.conversation_history.append({"id": user_turn_id, "role": "user", "content": user_message})

    # Build Gemini-compatible content
    contents = gemini_client.build_contents(history)
    tools = gemini_client.build_tool_declarations(tool_defs) if tool_defs else None

    # Agent loop: call Gemini, handle tool calls, repeat until text response
    all_tool_calls = []
    all_tool_responses = []
    all_raw_requests = []
    all_raw_responses = []
    total_token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total": 0}
    final_text = ""
    max_iterations = 10

    for iteration in range(max_iterations):
        try:
            result = await gemini_client.generate(
                system_prompt=system_prompt,
                model=model,
                contents=contents,
                tools=tools,
            )
        except Exception as e:
            yield {"type": "error", "message": f"Gemini API error: {str(e)}"}
            return

        all_raw_requests.append(result["raw_request"])
        all_raw_responses.append(result["raw_response"])

        if result["token_usage"]:
            for key in total_token_usage:
                total_token_usage[key] += result["token_usage"].get(key, 0) or 0

        # Check for function calls
        if result["function_calls"]:
            # --- ADK-style: group all function calls into one Content(role="model") ---
            fc_parts = []
            for fc in result["function_calls"]:
                fc_parts.append(types.Part.from_function_call(
                    name=fc["name"],
                    args=fc["args"],
                ))
                all_tool_calls.append(fc)
                yield {"type": "tool_call", "tool_name": fc["name"], "arguments": fc["args"]}

            contents.append(types.Content(role="model", parts=fc_parts))

            # --- ADK-style: execute all tools in parallel ---
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(
                    None,
                    _execute_tool_call,
                    fc["name"], fc["args"], state, tool_response_overrides,
                )
                for fc in result["function_calls"]
            ]
            tool_results = await asyncio.gather(*tasks)

            # --- ADK-style: group all function responses into one Content(role="user") ---
            fr_parts = []
            for fc, tool_result in zip(result["function_calls"], tool_results):
                all_tool_responses.append({"name": fc["name"], "response": tool_result})
                yield {"type": "tool_response", "tool_name": fc["name"], "result": tool_result}

                resp = tool_result if isinstance(tool_result, dict) else {"result": tool_result}
                fr_parts.append(types.Part.from_function_response(
                    name=fc["name"],
                    response=resp,
                ))

            contents.append(types.Content(role="user", parts=fr_parts))

            # Continue loop to get next Gemini response
            continue

        # Text response — stream it
        if result["text"]:
            final_text = result["text"]
            # Stream in chunks
            words = final_text.split(" ")
            for i in range(0, len(words), 3):
                chunk = " ".join(words[i:i+3])
                if i > 0:
                    chunk = " " + chunk
                yield {"type": "agent_chunk", "content": chunk}
        break

    # Save agent turn to DB
    agent_turn_id = str(uuid4())
    turn_index = len(state.conversation_history)

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO turns (id, session_id, turn_index, role, content,
               raw_request, raw_response, tool_calls, tool_responses, token_usage)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                agent_turn_id, state.session_id, turn_index, "agent", final_text,
                json.dumps(all_raw_requests),
                json.dumps(all_raw_responses),
                json.dumps(all_tool_calls) if all_tool_calls else None,
                json.dumps(all_tool_responses) if all_tool_responses else None,
                json.dumps(total_token_usage),
            ),
        )
        await db.commit()
    finally:
        await db.close()

    state.conversation_history.append({
        "id": agent_turn_id,
        "role": "agent",
        "content": final_text,
    })

    # Store tool calls/responses grouped (matching ADK's content structure)
    # All tool_call turns first, then all tool_response turns
    # so build_contents can group them into single Content objects
    for tc in all_tool_calls:
        state.conversation_history.append({
            "role": "tool_call",
            "content": json.dumps(tc),
            "tool_call": tc,
        })
    for tr in all_tool_responses:
        state.conversation_history.append({
            "role": "tool_response",
            "content": json.dumps(tr["response"]),
            "tool_response": tr,
        })

    # Yield complete turn
    yield {
        "type": "turn_complete",
        "turn": {
            "id": agent_turn_id,
            "session_id": state.session_id,
            "turn_index": turn_index,
            "role": "agent",
            "content": final_text,
            "raw_request": all_raw_requests,
            "raw_response": all_raw_responses,
            "tool_calls": all_tool_calls,
            "tool_responses": all_tool_responses,
            "token_usage": total_token_usage,
        },
    }


async def rerun_turn(
    state: SessionState,
    turn_id: str,
    overrides: dict,
) -> AsyncGenerator[dict, None]:
    """Rerun from a specific turn with optional overrides."""
    db = await get_db()
    try:
        # Find the original turn
        cursor = await db.execute("SELECT * FROM turns WHERE id = ?", (turn_id,))
        original_turn = await cursor.fetchone()
        if not original_turn:
            yield {"type": "error", "message": f"Turn {turn_id} not found"}
            return

        turn_index = original_turn["turn_index"]

        # Get history up to (but not including) this turn
        cursor = await db.execute(
            "SELECT * FROM turns WHERE session_id = ? AND is_active = 1 AND turn_index < ? ORDER BY turn_index ASC",
            (state.session_id, turn_index),
        )
        prior_turns = await cursor.fetchall()

        # Mark original turn and all subsequent turns as inactive
        await db.execute(
            "UPDATE turns SET is_active = 0 WHERE session_id = ? AND is_active = 1 AND turn_index >= ?",
            (state.session_id, turn_index),
        )
        await db.commit()
    finally:
        await db.close()

    # Rebuild history from prior turns
    history = []
    for row in prior_turns:
        turn = {"role": row["role"], "content": row["content"]}
        if row["tool_calls"]:
            tc = json.loads(row["tool_calls"])
            if tc:
                turn["tool_call"] = tc[0] if isinstance(tc, list) else tc
        if row["tool_responses"]:
            tr = json.loads(row["tool_responses"])
            if tr:
                turn["tool_response"] = tr[0] if isinstance(tr, list) else tr
        history.append(turn)

    # Rebuild state's conversation history
    state.conversation_history = history

    # Apply overrides
    system_prompt_override = overrides.get("system_prompt")
    tool_response_overrides = overrides.get("tool_responses")
    modified_history = overrides.get("modified_history", history)

    # Run agent turn with overrides
    async for event in run_agent_turn(
        state,
        system_prompt_override=system_prompt_override,
        tool_response_overrides=tool_response_overrides,
        modified_history=modified_history,
    ):
        yield event
