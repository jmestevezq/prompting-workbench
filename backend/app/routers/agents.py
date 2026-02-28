import json
import hashlib
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse,
    PromptVersionResponse, PromptVersionCreate, PromptVersionLabelUpdate,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[AgentResponse])
async def list_agents():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agents ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_agent(row) for row in rows]
    finally:
        await db.close()


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(agent: AgentCreate):
    db = await get_db()
    try:
        agent_id = str(uuid4())
        await db.execute(
            "INSERT INTO agents (id, name, system_prompt, model, tool_definitions) VALUES (?, ?, ?, ?, ?)",
            (agent_id, agent.name, agent.system_prompt, agent.model, json.dumps(agent.tool_definitions)),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        return _row_to_agent(row)
    finally:
        await db.close()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")
        return _row_to_agent(row)
    finally:
        await db.close()


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(agent_id: str, update: AgentUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Agent not found")

        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.system_prompt is not None:
            fields.append("system_prompt = ?")
            values.append(update.system_prompt)
        if update.model is not None:
            fields.append("model = ?")
            values.append(update.model)
        if update.tool_definitions is not None:
            fields.append("tool_definitions = ?")
            values.append(json.dumps(update.tool_definitions))

        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            values.append(agent_id)
            await db.execute(f"UPDATE agents SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        return _row_to_agent(row)
    finally:
        await db.close()


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Agent not found")
        await db.execute("DELETE FROM agents WHERE id = ?", (agent_id,))
        await db.commit()
    finally:
        await db.close()


# --- Prompt Versions ---

@router.get("/{agent_id}/versions", response_model=list[PromptVersionResponse])
async def list_prompt_versions(agent_id: str):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM prompt_versions WHERE agent_id = ? ORDER BY created_at DESC",
            (agent_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_version(row) for row in rows]
    finally:
        await db.close()


@router.post("/{agent_id}/versions", response_model=PromptVersionResponse, status_code=201)
async def create_prompt_version(agent_id: str, body: PromptVersionCreate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        agent_row = await cursor.fetchone()
        if not agent_row:
            raise HTTPException(status_code=404, detail="Agent not found")

        system_prompt = agent_row["system_prompt"]
        tool_definitions = agent_row["tool_definitions"]
        version_hash = hashlib.sha256(
            (system_prompt + (tool_definitions or "")).encode()
        ).hexdigest()[:16]

        version_id = str(uuid4())
        await db.execute(
            "INSERT INTO prompt_versions (id, agent_id, system_prompt, tool_definitions, version_hash, label) VALUES (?, ?, ?, ?, ?, ?)",
            (version_id, agent_id, system_prompt, tool_definitions, version_hash, body.label),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM prompt_versions WHERE id = ?", (version_id,))
        row = await cursor.fetchone()
        return _row_to_version(row)
    finally:
        await db.close()


@router.post("/{agent_id}/versions/{version_id}/label", response_model=PromptVersionResponse)
async def update_version_label(agent_id: str, version_id: str, body: PromptVersionLabelUpdate):
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM prompt_versions WHERE id = ? AND agent_id = ?",
            (version_id, agent_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Version not found")

        await db.execute("UPDATE prompt_versions SET label = ? WHERE id = ?", (body.label, version_id))
        await db.commit()

        cursor = await db.execute("SELECT * FROM prompt_versions WHERE id = ?", (version_id,))
        row = await cursor.fetchone()
        return _row_to_version(row)
    finally:
        await db.close()


def _row_to_agent(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "system_prompt": row["system_prompt"],
        "model": row["model"],
        "tool_definitions": json.loads(row["tool_definitions"]) if row["tool_definitions"] else [],
        "created_at": row["created_at"] or "",
        "updated_at": row["updated_at"] or "",
    }


def _row_to_version(row) -> dict:
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "system_prompt": row["system_prompt"],
        "tool_definitions": json.loads(row["tool_definitions"]) if row["tool_definitions"] else None,
        "version_hash": row["version_hash"],
        "label": row["label"],
        "created_at": row["created_at"] or "",
    }
