import json
import hashlib
from uuid import uuid4
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.database import get_db
from app.schemas.classification import (
    GoldenTransactionCreate, GoldenTransactionUpdate, GoldenTransactionResponse,
    GoldenTransactionImport,
    ClassificationPromptCreate, ClassificationPromptUpdate, ClassificationPromptResponse,
    ClassificationRunCreate, ClassificationRunResponse, ClassificationResultResponse,
)
from app.services.batch_runner import run_batch
from app.services.metrics import compute_classification_metrics
from app.services.matchers import match_transaction_lists
from app.services import gemini_client

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

@router.post("/api/classification/run", response_model=ClassificationRunResponse, status_code=201)
async def start_classification_run(body: ClassificationRunCreate, background_tasks: BackgroundTasks):
    db = await get_db()
    try:
        # Validate prompt exists
        cursor = await db.execute("SELECT * FROM classification_prompts WHERE id = ?", (body.prompt_id,))
        prompt_row = await cursor.fetchone()
        if not prompt_row:
            raise HTTPException(status_code=404, detail="Classification prompt not found")

        prompt_hash = hashlib.sha256(prompt_row["prompt_template"].encode()).hexdigest()[:16]

        run_id = str(uuid4())
        await db.execute(
            "INSERT INTO classification_runs (id, prompt_id, prompt_version_hash, golden_set_name, status) VALUES (?, ?, ?, ?, ?)",
            (run_id, body.prompt_id, prompt_hash, body.golden_set_name, "running"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM classification_runs WHERE id = ?", (run_id,))
        run_row = await cursor.fetchone()
    finally:
        await db.close()

    background_tasks.add_task(
        _execute_classification_run,
        run_id,
        prompt_row["prompt_template"],
        prompt_row["model"],
        body.golden_set_name,
    )

    return _row_to_run(run_row)


async def _execute_classification_run(run_id: str, prompt_template: str, model: str, golden_set_name: str):
    """Execute classification eval: render prompt per golden entry, call Gemini, compare."""
    import re

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM golden_transactions WHERE set_name = ?", (golden_set_name,)
        )
        golden_rows = await cursor.fetchall()
    finally:
        await db.close()

    if not golden_rows:
        db = await get_db()
        try:
            await db.execute(
                "UPDATE classification_runs SET status = 'failed', metrics = ? WHERE id = ?",
                (json.dumps({"error": "No golden set entries found"}), run_id),
            )
            await db.commit()
        finally:
            await db.close()
        return

    golden_entries = [_row_to_golden(row) for row in golden_rows]

    async def process_entry(entry):
        # Render prompt template
        prompt = prompt_template
        prompt = prompt.replace("{{input_transactions}}", json.dumps(entry["input_transactions"], indent=2))
        ref = entry.get("reference_transactions") or {}
        if isinstance(ref, dict):
            prompt = prompt.replace("{{reference_list_1}}", json.dumps(ref.get("list_1", []), indent=2))
            prompt = prompt.replace("{{reference_list_2}}", json.dumps(ref.get("list_2", []), indent=2))
            prompt = prompt.replace("{{reference_list_3}}", json.dumps(ref.get("list_3", []), indent=2))
        elif isinstance(ref, list) and len(ref) >= 3:
            prompt = prompt.replace("{{reference_list_1}}", json.dumps(ref[0], indent=2))
            prompt = prompt.replace("{{reference_list_2}}", json.dumps(ref[1], indent=2))
            prompt = prompt.replace("{{reference_list_3}}", json.dumps(ref[2], indent=2))

        contents = gemini_client.build_contents([], user_message=prompt)
        try:
            result = await gemini_client.generate(
                system_prompt="You are a transaction classifier. Respond with a JSON array of classified transactions.",
                model=model,
                contents=contents,
            )
            text = result.get("text", "")
            predicted = _parse_json_array(text)
            match_details = match_transaction_lists(predicted, entry["expected_output"])

            return {
                "golden_id": entry["id"],
                "predicted_output": predicted,
                "expected_output": entry["expected_output"],
                "match_details": match_details,
                "raw_response": result.get("raw_response"),
                "token_usage": result.get("token_usage"),
            }
        except Exception as e:
            return {
                "golden_id": entry["id"],
                "predicted_output": [],
                "expected_output": entry["expected_output"],
                "match_details": {"error": str(e)},
                "raw_response": None,
                "token_usage": None,
            }

    results = await run_batch(golden_entries, process_entry)

    # Save results and compute metrics
    db = await get_db()
    try:
        for r in results:
            result_id = str(uuid4())
            await db.execute(
                "INSERT INTO classification_results (id, run_id, golden_id, predicted_output, match_details, raw_response, token_usage) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    result_id, run_id, r["golden_id"],
                    json.dumps(r["predicted_output"]),
                    json.dumps(r["match_details"]),
                    json.dumps(r["raw_response"]) if r["raw_response"] else None,
                    json.dumps(r["token_usage"]) if r["token_usage"] else None,
                ),
            )

        metrics = compute_classification_metrics(results)

        await db.execute(
            "UPDATE classification_runs SET status = 'completed', metrics = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(metrics), run_id),
        )
        await db.commit()
    except Exception as e:
        await db.execute(
            "UPDATE classification_runs SET status = 'failed', metrics = ? WHERE id = ?",
            (json.dumps({"error": str(e)}), run_id),
        )
        await db.commit()
    finally:
        await db.close()


def _parse_json_array(text: str) -> list:
    """Parse a JSON array from Gemini response."""
    import re
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
        return [result]
    except json.JSONDecodeError:
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return []


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
