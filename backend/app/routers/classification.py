import json
from uuid import uuid4
from fastapi import APIRouter, HTTPException

from app.database import get_db
from app.schemas.classification import (
    GoldenTransactionCreate, GoldenTransactionUpdate, GoldenTransactionResponse,
    GoldenTransactionImport,
    ClassificationPromptCreate, ClassificationPromptUpdate, ClassificationPromptResponse,
    ClassificationRunResponse, ClassificationResultResponse,
)

router = APIRouter(tags=["classification"])


# --- Golden Sets ---

@router.get("/api/golden-sets", response_model=list[GoldenTransactionResponse])
async def list_golden_sets():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM golden_transactions ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_golden(row) for row in rows]
    finally:
        await db.close()


@router.post("/api/golden-sets", response_model=GoldenTransactionResponse, status_code=201)
async def create_golden_set(item: GoldenTransactionCreate):
    db = await get_db()
    try:
        item_id = str(uuid4())
        await db.execute(
            "INSERT INTO golden_transactions (id, set_name, input_transactions, reference_transactions, expected_output, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (
                item_id, item.set_name,
                json.dumps(item.input_transactions),
                json.dumps(item.reference_transactions) if item.reference_transactions else None,
                json.dumps(item.expected_output),
                json.dumps(item.tags),
            ),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM golden_transactions WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        return _row_to_golden(row)
    finally:
        await db.close()


@router.put("/api/golden-sets/{item_id}", response_model=GoldenTransactionResponse)
async def update_golden_set(item_id: str, update: GoldenTransactionUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM golden_transactions WHERE id = ?", (item_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Golden set item not found")

        fields = []
        values = []
        if update.set_name is not None:
            fields.append("set_name = ?")
            values.append(update.set_name)
        if update.input_transactions is not None:
            fields.append("input_transactions = ?")
            values.append(json.dumps(update.input_transactions))
        if update.reference_transactions is not None:
            fields.append("reference_transactions = ?")
            values.append(json.dumps(update.reference_transactions))
        if update.expected_output is not None:
            fields.append("expected_output = ?")
            values.append(json.dumps(update.expected_output))
        if update.tags is not None:
            fields.append("tags = ?")
            values.append(json.dumps(update.tags))

        if fields:
            values.append(item_id)
            await db.execute(f"UPDATE golden_transactions SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM golden_transactions WHERE id = ?", (item_id,))
        row = await cursor.fetchone()
        return _row_to_golden(row)
    finally:
        await db.close()


@router.post("/api/golden-sets/import", response_model=list[GoldenTransactionResponse], status_code=201)
async def import_golden_sets(data: GoldenTransactionImport):
    db = await get_db()
    try:
        results = []
        for item in data.items:
            item_id = str(uuid4())
            await db.execute(
                "INSERT INTO golden_transactions (id, set_name, input_transactions, reference_transactions, expected_output, tags) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item_id, item.set_name,
                    json.dumps(item.input_transactions),
                    json.dumps(item.reference_transactions) if item.reference_transactions else None,
                    json.dumps(item.expected_output),
                    json.dumps(item.tags),
                ),
            )
            cursor = await db.execute("SELECT * FROM golden_transactions WHERE id = ?", (item_id,))
            row = await cursor.fetchone()
            results.append(_row_to_golden(row))
        await db.commit()
        return results
    finally:
        await db.close()


# --- Classification Prompts ---

@router.get("/api/classification/prompts", response_model=list[ClassificationPromptResponse])
async def list_classification_prompts():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classification_prompts ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_prompt(row) for row in rows]
    finally:
        await db.close()


@router.post("/api/classification/prompts", response_model=ClassificationPromptResponse, status_code=201)
async def create_classification_prompt(prompt: ClassificationPromptCreate):
    db = await get_db()
    try:
        prompt_id = str(uuid4())
        await db.execute(
            "INSERT INTO classification_prompts (id, name, prompt_template, model) VALUES (?, ?, ?, ?)",
            (prompt_id, prompt.name, prompt.prompt_template, prompt.model),
        )
        await db.commit()
        cursor = await db.execute("SELECT * FROM classification_prompts WHERE id = ?", (prompt_id,))
        row = await cursor.fetchone()
        return _row_to_prompt(row)
    finally:
        await db.close()


@router.put("/api/classification/prompts/{prompt_id}", response_model=ClassificationPromptResponse)
async def update_classification_prompt(prompt_id: str, update: ClassificationPromptUpdate):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classification_prompts WHERE id = ?", (prompt_id,))
        if not await cursor.fetchone():
            raise HTTPException(status_code=404, detail="Classification prompt not found")

        fields = []
        values = []
        if update.name is not None:
            fields.append("name = ?")
            values.append(update.name)
        if update.prompt_template is not None:
            fields.append("prompt_template = ?")
            values.append(update.prompt_template)
        if update.model is not None:
            fields.append("model = ?")
            values.append(update.model)

        if fields:
            values.append(prompt_id)
            await db.execute(f"UPDATE classification_prompts SET {', '.join(fields)} WHERE id = ?", values)
            await db.commit()

        cursor = await db.execute("SELECT * FROM classification_prompts WHERE id = ?", (prompt_id,))
        row = await cursor.fetchone()
        return _row_to_prompt(row)
    finally:
        await db.close()


# --- Classification Runs ---

@router.get("/api/classification/runs", response_model=list[ClassificationRunResponse])
async def list_classification_runs():
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classification_runs ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_run(row) for row in rows]
    finally:
        await db.close()


@router.get("/api/classification/runs/{run_id}", response_model=ClassificationRunResponse)
async def get_classification_run(run_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classification_runs WHERE id = ?", (run_id,))
        row = await cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Classification run not found")
        return _row_to_run(row)
    finally:
        await db.close()


@router.get("/api/classification/runs/{run_id}/results", response_model=list[ClassificationResultResponse])
async def get_classification_results(run_id: str):
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM classification_results WHERE run_id = ?", (run_id,))
        rows = await cursor.fetchall()
        return [_row_to_result(row) for row in rows]
    finally:
        await db.close()


# --- Row helpers ---

def _row_to_golden(row) -> dict:
    return {
        "id": row["id"],
        "set_name": row["set_name"],
        "input_transactions": json.loads(row["input_transactions"]) if row["input_transactions"] else [],
        "reference_transactions": json.loads(row["reference_transactions"]) if row["reference_transactions"] else None,
        "expected_output": json.loads(row["expected_output"]) if row["expected_output"] else [],
        "tags": json.loads(row["tags"]) if row["tags"] else [],
        "created_at": row["created_at"] or "",
    }


def _row_to_prompt(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "prompt_template": row["prompt_template"],
        "model": row["model"],
        "created_at": row["created_at"] or "",
    }


def _row_to_run(row) -> dict:
    return {
        "id": row["id"],
        "prompt_id": row["prompt_id"],
        "prompt_version_hash": row["prompt_version_hash"],
        "golden_set_name": row["golden_set_name"],
        "status": row["status"],
        "metrics": json.loads(row["metrics"]) if row["metrics"] else None,
        "created_at": row["created_at"] or "",
        "completed_at": row["completed_at"],
    }


def _row_to_result(row) -> dict:
    return {
        "id": row["id"],
        "run_id": row["run_id"],
        "golden_id": row["golden_id"],
        "predicted_output": json.loads(row["predicted_output"]) if row["predicted_output"] else [],
        "match_details": json.loads(row["match_details"]) if row["match_details"] else None,
        "raw_response": json.loads(row["raw_response"]) if row["raw_response"] else None,
        "token_usage": json.loads(row["token_usage"]) if row["token_usage"] else None,
    }
