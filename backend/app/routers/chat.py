"""WebSocket handler for the agent chat playground."""

import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.agent_runtime import SessionState, run_agent_turn, rerun_turn

router = APIRouter()

# Active sessions: session_id -> SessionState
active_sessions: dict[str, SessionState] = {}


@router.websocket("/ws/chat/{session_id}")
async def chat_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Get or create session state
    if session_id not in active_sessions:
        state = SessionState(session_id)
        try:
            await state.load()
        except Exception as e:
            await websocket.send_json({"type": "error", "message": str(e)})
            await websocket.close()
            return
        active_sessions[session_id] = state
    else:
        state = active_sessions[session_id]

    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = message.get("type")

            if msg_type == "user_message":
                content = message.get("content", "").strip()
                if not content:
                    await websocket.send_json({"type": "error", "message": "Empty message"})
                    continue

                async for event in run_agent_turn(state, user_message=content):
                    await websocket.send_json(_serialize_event(event))

            elif msg_type == "rerun_turn":
                turn_id = message.get("turn_id")
                overrides = message.get("overrides", {})
                if not turn_id:
                    await websocket.send_json({"type": "error", "message": "Missing turn_id"})
                    continue

                async for event in rerun_turn(state, turn_id, overrides):
                    await websocket.send_json(_serialize_event(event))

            elif msg_type == "swap_fixture":
                fixture_ids = message.get("fixture_ids", [])
                try:
                    await state.swap_fixtures(fixture_ids)
                    await websocket.send_json({
                        "type": "fixture_swapped",
                        "fixture_ids": fixture_ids,
                    })
                except Exception as e:
                    await websocket.send_json({"type": "error", "message": str(e)})

            elif msg_type == "set_tool_override":
                overrides = message.get("overrides", {})
                state.tool_overrides.update(overrides)
                await websocket.send_json({
                    "type": "tool_overrides_updated",
                    "overrides": state.tool_overrides,
                })

            elif msg_type == "clear_tool_overrides":
                state.tool_overrides.clear()
                await websocket.send_json({
                    "type": "tool_overrides_cleared",
                })

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        # Clean up session state on disconnect
        active_sessions.pop(session_id, None)


def _serialize_event(event: dict) -> dict:
    """Ensure event is JSON-serializable."""
    try:
        json.dumps(event)
        return event
    except (TypeError, ValueError):
        # Fallback: convert non-serializable values to strings
        return json.loads(json.dumps(event, default=str))
