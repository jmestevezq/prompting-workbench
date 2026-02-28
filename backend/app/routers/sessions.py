import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas.session import SessionCreate, SessionResponse, TurnResponse

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionResponse])
async def list_sessions():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_session(row) for row in rows]
    finally:
        await db.close()


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(session: SessionCreate):
    db = await get_db()
    try:
        session_id = str(uuid4())
        await db.execute(
            "INSERT INTO sessions (id, agent_id, fixture_ids, prompt_version_id) VALUES (?, ?, ?, ?)",
            (session_id, session.agent_id, json.dumps(session.fixture_ids), session.prompt_version_id),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        return _row_to_session(row)
    finally:
        await db.close()


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Session not found")
        return _row_to_session(row)
    finally:
        await db.close()


@router.get("/{session_id}/turns", response_model=list[TurnResponse])
async def list_turns(session_id: str, active_only: bool = True):
    db = await get_db()
    try:
        if active_only:
            cursor = await db.execute(
                "SELECT * FROM turns WHERE session_id = ? AND is_active = 1 ORDER BY turn_index ASC",
                (session_id,),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM turns WHERE session_id = ? ORDER BY turn_index ASC",
                (session_id,),
            )
        rows = await cursor.fetchall()
        return [_row_to_turn(row) for row in rows]
    finally:
        await db.close()


def _row_to_session(row) -> dict:
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "fixture_ids": json.loads(row["fixture_ids"]) if row["fixture_ids"] else [],
        "prompt_version_id": row["prompt_version_id"],
        "created_at": row["created_at"] or "",
    }


def _row_to_turn(row) -> dict:
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "turn_index": row["turn_index"],
        "role": row["role"],
        "content": row["content"],
        "raw_request": json.loads(row["raw_request"]) if row["raw_request"] else None,
        "raw_response": json.loads(row["raw_response"]) if row["raw_response"] else None,
        "tool_calls": json.loads(row["tool_calls"]) if row["tool_calls"] else None,
        "tool_responses": json.loads(row["tool_responses"]) if row["tool_responses"] else None,
        "token_usage": json.loads(row["token_usage"]) if row["token_usage"] else None,
        "parent_turn_id": row["parent_turn_id"],
        "is_active": row["is_active"],
        "created_at": row["created_at"] or "",
    }
