import json
import hashlib
from pathlib import Path
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.database import get_db
from app.schemas.agent import (
    AgentCreate, AgentUpdate, AgentResponse,
    PromptVersionResponse, PromptVersionCreate, PromptVersionLabelUpdate,
    AgentVersionResponse, AgentVersionCreate, AgentImportResponse, AgentTemplateResponse,
)
from app.services.agent_loader import load_agent_from_folder, list_agent_folders, AgentLoadError

router = APIRouter(prefix="/api/agents", tags=["agents"])


# --- Routes with fixed prefixes (must come before /{agent_id} catch-all) ---

@router.get("/folders/available")
async def list_available_agent_folders():
    """List agent folders available for import."""
    folders = list_agent_folders(settings.AGENTS_DIR)
    return {"folders": folders}


@router.post("/import/{folder_name}", response_model=AgentImportResponse)
async def import_agent_from_folder(folder_name: str):
    """Import or re-import an agent from a folder in the agents directory."""
    agents_dir = Path(settings.AGENTS_DIR)
    folder_path = agents_dir / folder_name

    try:
        snapshot = load_agent_from_folder(folder_path)
    except AgentLoadError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db = await get_db()
    try:
        # Check if agent with this folder already exists
        cursor = await db.execute("SELECT id FROM agents WHERE agent_folder = ?", (folder_name,))
        existing = await cursor.fetchone()

        if existing:
            agent_id = existing["id"]
            # Update agent record
            await db.execute(
                """UPDATE agents SET name = ?, system_prompt = ?, model = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (snapshot.name, snapshot.system_prompt, snapshot.model, agent_id),
            )

            # Update existing base version
            cursor = await db.execute(
                "SELECT id FROM agent_versions WHERE agent_id = ? AND is_base = 1",
                (agent_id,),
            )
            base_version = await cursor.fetchone()

            if base_version:
                version_id = base_version["id"]
                await db.execute(
                    """UPDATE agent_versions SET
                       version_label = ?, raw_template = ?, variables = ?,
                       variable_definitions = ?, system_prompt = ?,
                       tool_details = ?, widget_details = ?, tools = ?
                       WHERE id = ?""",
                    (
                        f"Base ({snapshot.version})",
                        snapshot.raw_template,
                        json.dumps(snapshot.variables),
                        json.dumps(snapshot.variable_definitions),
                        snapshot.system_prompt,
                        json.dumps(snapshot.tool_details),
                        json.dumps(snapshot.widget_details),
                        json.dumps(snapshot.tools),
                        version_id,
                    ),
                )
            else:
                version_id = str(uuid4())
                await db.execute(
                    """INSERT INTO agent_versions
                       (id, agent_id, version_label, source, raw_template, variables,
                        variable_definitions, system_prompt, tool_details, widget_details, tools, is_base)
                       VALUES (?, ?, ?, 'file', ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (
                        version_id, agent_id, f"Base ({snapshot.version})",
                        snapshot.raw_template,
                        json.dumps(snapshot.variables),
                        json.dumps(snapshot.variable_definitions),
                        snapshot.system_prompt,
                        json.dumps(snapshot.tool_details),
                        json.dumps(snapshot.widget_details),
                        json.dumps(snapshot.tools),
                    ),
                )

            # Set as active version
            await db.execute(
                "UPDATE agents SET active_version_id = ? WHERE id = ?",
                (version_id, agent_id),
            )
            await db.commit()
            message = "Agent re-imported successfully"

        else:
            # Create new agent (without active_version_id first to avoid FK issue)
            agent_id = str(uuid4())
            version_id = str(uuid4())

            await db.execute(
                """INSERT INTO agents (id, name, system_prompt, model, tool_definitions, agent_folder)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    agent_id, snapshot.name, snapshot.system_prompt,
                    snapshot.model, json.dumps([]),
                    folder_name,
                ),
            )

            await db.execute(
                """INSERT INTO agent_versions
                   (id, agent_id, version_label, source, raw_template, variables,
                    variable_definitions, system_prompt, tool_details, widget_details, tools, is_base)
                   VALUES (?, ?, ?, 'file', ?, ?, ?, ?, ?, ?, ?, 1)""",
                (
                    version_id, agent_id, f"Base ({snapshot.version})",
                    snapshot.raw_template,
                    json.dumps(snapshot.variables),
                    json.dumps(snapshot.variable_definitions),
                    snapshot.system_prompt,
                    json.dumps(snapshot.tool_details),
                    json.dumps(snapshot.widget_details),
                    json.dumps(snapshot.tools),
                ),
            )

            # Now set active version
            await db.execute(
                "UPDATE agents SET active_version_id = ? WHERE id = ?",
                (version_id, agent_id),
            )
            await db.commit()
            message = "Agent imported successfully"

        return {
            "agent_id": agent_id,
            "version_id": version_id,
            "name": snapshot.name,
            "version_label": f"Base ({snapshot.version})",
            "message": message,
        }
    finally:
        await db.close()


# --- Agent CRUD ---

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


# --- Agent Versions ---

@router.get("/{agent_id}/agent-versions", response_model=list[AgentVersionResponse])
async def list_agent_versions(agent_id: str):
    """List all versions for an agent (base first, then UI versions by date)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM agent_versions WHERE agent_id = ? ORDER BY is_base DESC, created_at DESC",
            (agent_id,),
        )
        rows = await cursor.fetchall()
        return [_row_to_agent_version(row) for row in rows]
    finally:
        await db.close()


@router.post("/{agent_id}/agent-versions", response_model=AgentVersionResponse, status_code=201)
async def create_agent_version(agent_id: str, body: AgentVersionCreate):
    """Create a new version from UI edits (full snapshot)."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Agent not found")

        version_id = str(uuid4())
        await db.execute(
            """INSERT INTO agent_versions
               (id, agent_id, version_label, source, raw_template, variables,
                variable_definitions, system_prompt, tool_details, widget_details, tools, is_base)
               VALUES (?, ?, ?, 'ui', ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                version_id, agent_id, body.version_label,
                body.raw_template,
                json.dumps(body.variables) if body.variables else None,
                json.dumps(body.variable_definitions) if body.variable_definitions else None,
                body.system_prompt,
                json.dumps(body.tool_details) if body.tool_details else None,
                json.dumps(body.widget_details) if body.widget_details else None,
                json.dumps(body.tools) if body.tools else None,
            ),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM agent_versions WHERE id = ?", (version_id,))
        row = await cursor.fetchone()
        return _row_to_agent_version(row)
    finally:
        await db.close()


@router.put("/{agent_id}/active-version", response_model=AgentResponse)
async def set_active_version(agent_id: str, version_id: str):
    """Switch the active version for an agent."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT id FROM agents WHERE id = ?", (agent_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Agent not found")

        # Verify version exists and belongs to this agent
        cursor = await db.execute(
            "SELECT id FROM agent_versions WHERE id = ? AND agent_id = ?",
            (version_id, agent_id),
        )
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Version not found for this agent")

        await db.execute(
            "UPDATE agents SET active_version_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (version_id, agent_id),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        row = await cursor.fetchone()
        return _row_to_agent(row)
    finally:
        await db.close()


@router.get("/{agent_id}/template", response_model=AgentTemplateResponse)
async def get_agent_template(agent_id: str):
    """Get the raw template + variables for the active version."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM agents WHERE id = ?", (agent_id,))
        agent = await cursor.fetchone()
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")

        active_version_id = None
        try:
            active_version_id = agent["active_version_id"]
        except (IndexError, KeyError):
            pass

        if active_version_id:
            cursor = await db.execute("SELECT * FROM agent_versions WHERE id = ?", (active_version_id,))
            version = await cursor.fetchone()
            if version:
                return {
                    "raw_template": version["raw_template"],
                    "variables": json.loads(version["variables"]) if version["variables"] else None,
                    "variable_definitions": json.loads(version["variable_definitions"]) if version["variable_definitions"] else None,
                    "system_prompt": version["system_prompt"],
                    "tool_details": json.loads(version["tool_details"]) if version["tool_details"] else None,
                    "widget_details": json.loads(version["widget_details"]) if version["widget_details"] else None,
                }

        # No active version — return agent's current prompt
        return {
            "raw_template": None,
            "variables": None,
            "variable_definitions": None,
            "system_prompt": agent["system_prompt"],
            "tool_details": None,
            "widget_details": None,
        }
    finally:
        await db.close()


def _row_to_agent_version(row) -> dict:
    return {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "version_label": row["version_label"],
        "source": row["source"],
        "raw_template": row["raw_template"],
        "variables": json.loads(row["variables"]) if row["variables"] else None,
        "variable_definitions": json.loads(row["variable_definitions"]) if row["variable_definitions"] else None,
        "system_prompt": row["system_prompt"],
        "tool_details": json.loads(row["tool_details"]) if row["tool_details"] else None,
        "widget_details": json.loads(row["widget_details"]) if row["widget_details"] else None,
        "tools": json.loads(row["tools"]) if row["tools"] else None,
        "is_base": bool(row["is_base"]),
        "created_at": row["created_at"] or "",
    }


def _row_to_agent(row) -> dict:
    result = {
        "id": row["id"],
        "name": row["name"],
        "system_prompt": row["system_prompt"],
        "model": row["model"],
        "tool_definitions": json.loads(row["tool_definitions"]) if row["tool_definitions"] else [],
        "created_at": row["created_at"] or "",
        "updated_at": row["updated_at"] or "",
    }
    # Add new columns if present (handles pre-migration rows)
    try:
        result["agent_folder"] = row["agent_folder"]
    except (IndexError, KeyError):
        result["agent_folder"] = None
    try:
        result["active_version_id"] = row["active_version_id"]
    except (IndexError, KeyError):
        result["active_version_id"] = None
    return result


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
