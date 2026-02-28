import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas.autorater import (
    AutoraterCreate, AutoraterUpdate, AutoraterResponse,
    EvalRunResponse, EvalResultResponse,
)

router = APIRouter(tags=["autoraters"])


# --- Autorater CRUD ---

@router.get("/api/autoraters", response_model=list[AutoraterResponse])
async def list_autoraters():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM autoraters ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_autorater(row) for row in rows]
    finally:
        await db.close()


@router.post("/api/autoraters", response_model=AutoraterResponse, status_code=201)
async def create_autorater(autorater: AutoraterCreate):
    db = await get_db()
    try:
        autorater_id = str(uuid4())
        await db.execute(
            "INSERT INTO autoraters (id, name, prompt, model, output_schema) VALUES (?, ?, ?, ?, ?)",
            (autorater_id, autorater.name, autorater.prompt, autorater.model,
             json.dumps(autorater.output_schema) if autorater.output_schema else None),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM autoraters WHERE id = ?", (autorater_id,))
        row = await cursor.fetchone()
        return _row_to_autorater(row)
    finally:
        await db.close()


@router.get("/api/autoraters/{autorater_id}", response_model=AutoraterResponse)
async def get_autorater(autorater_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM autoraters WHERE id = ?", (autorater_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Autorater not found")
        return _row_to_autorater(row)
    finally:
        await db.close()


@router.put("/api/autoraters/{autorater_id}", response_model=AutoraterResponse)
async def update_autorater(autorater_id: str, update: AutoraterUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM autoraters WHERE id = ?", (autorater_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Autorater not found")

        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.prompt is not None:
            fields.append("prompt = ?")
            values.append(update.prompt)
        if update.model is not None:
            fields.append("model = ?")
            values.append(update.model)
        if update.output_schema is not None:
            fields.append("output_schema = ?")
            values.append(json.dumps(update.output_schema))

        if fields:
            values.append(autorater_id)
            await db.execute(f"UPDATE autoraters SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM autoraters WHERE id = ?", (autorater_id,))
        row = await cursor.fetchone()
        return _row_to_autorater(row)
    finally:
        await db.close()


# --- Eval Runs ---

@router.get("/api/eval/runs", response_model=list[EvalRunResponse])
async def list_eval_runs():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM eval_runs ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_eval_run(row) for row in rows]
    finally:
        await db.close()


@router.get("/api/eval/runs/{run_id}", response_model=EvalRunResponse)
async def get_eval_run(run_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Eval run not found")
        return _row_to_eval_run(row)
    finally:
        await db.close()


@router.get("/api/eval/runs/{run_id}/results", response_model=list[EvalResultResponse])
async def get_eval_results(run_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM eval_results WHERE run_id = ?", (run_id,))
        rows = await cursor.fetchall()
        return [_row_to_eval_result(row) for row in rows]
    finally:
        await db.close()


@router.get("/api/eval/runs/{run_id}/diff/{other_id}")
async def diff_eval_runs(run_id: str, other_id: str):
    db = await get_db()
    try:
        # Get results for both runs
        cursor_a = await db.execute("SELECT * FROM eval_results WHERE run_id = ?", (run_id,))
        results_a = await cursor_a.fetchall()
        cursor_b = await db.execute("SELECT * FROM eval_results WHERE run_id = ?", (other_id,))
        results_b = await cursor_b.fetchall()

        # Index by transcript_id
        map_a = {r["transcript_id"]: _row_to_eval_result(r) for r in results_a}
        map_b = {r["transcript_id"]: _row_to_eval_result(r) for r in results_b}

        all_ids = set(map_a.keys()) | set(map_b.keys())
        diff = []
        for tid in all_ids:
            ra = map_a.get(tid)
            rb = map_b.get(tid)
            diff.append({
                "transcript_id": tid,
                "run_a": ra,
                "run_b": rb,
                "changed": (ra is None or rb is None or ra.get("match") != rb.get("match")),
            })

        return {"run_a_id": run_id, "run_b_id": other_id, "diffs": diff}
    finally:
        await db.close()


def _row_to_autorater(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "prompt": row["prompt"],
        "model": row["model"],
        "output_schema": json.loads(row["output_schema"]) if row["output_schema"] else None,
        "created_at": row["created_at"] or "",
    }


def _row_to_eval_run(row) -> dict:
    return {
        "id": row["id"],
        "autorater_id": row["autorater_id"],
        "prompt_version_hash": row["prompt_version_hash"],
        "transcript_ids": json.loads(row["transcript_ids"]) if row["transcript_ids"] else [],
        "status": row["status"],
        "metrics": json.loads(row["metrics"]) if row["metrics"] else None,
        "created_at": row["created_at"] or "",
        "completed_at": row["completed_at"],
    }


def _row_to_eval_result(row) -> dict:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "transcript_id": row["transcript_id"],
        "predicted_labels": json.loads(row["predicted_labels"]) if row["predicted_labels"] else {},
        "ground_truth_labels": json.loads(row["ground_truth_labels"]) if row["ground_truth_labels"] else {},
        "match": bool(row["match"]) if row["match"] is not None else None,
        "raw_response": json.loads(row["raw_response"]) if row["raw_response"] else None,
        "token_usage": json.loads(row["token_usage"]) if row["token_usage"] else None,
    }
