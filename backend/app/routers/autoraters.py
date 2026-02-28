import json
import hashlib
from uuid import uuid4
from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.database import get_db
from app.schemas.autorater import (
    AutoraterCreate, AutoraterUpdate, AutoraterResponse,
    EvalRunCreate, EvalRunResponse, EvalResultResponse,
)
from app.services.batch_runner import run_batch
from app.services.metrics import compute_binary_metrics
from app.services import gemini_client

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


@router.post("/api/eval/run", response_model=EvalRunResponse, status_code=201)
async def start_eval_run(body: EvalRunCreate, background_tasks: BackgroundTasks):
    db = await get_db()
    try:
        # Validate autorater exists
        cursor = await db.execute("SELECT * FROM autoraters WHERE id = ?", (body.autorater_id,))
        autorater_row = await cursor.fetchone()
        if not autorater_row:
            raise HTTPException(status_code=404, detail="Autorater not found")

        prompt_hash = hashlib.sha256(autorater_row["prompt"].encode()).hexdigest()[:16]

        # Create eval run
        run_id = str(uuid4())
        await db.execute(
            "INSERT INTO eval_runs (id, autorater_id, prompt_version_hash, transcript_ids, eval_tags, status) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, body.autorater_id, prompt_hash, json.dumps(body.transcript_ids),
             json.dumps(body.eval_tags) if body.eval_tags else None,
             "running"),
        )
        await db.commit()

        cursor = await db.execute("SELECT * FROM eval_runs WHERE id = ?", (run_id,))
        run_row = await cursor.fetchone()
    finally:
        await db.close()

    # Run evaluation in background
    background_tasks.add_task(
        _execute_eval_run,
        run_id,
        autorater_row["prompt"],
        autorater_row["model"],
        body.transcript_ids,
        body.eval_tags or [],
    )

    return _row_to_eval_run(run_row)


async def _execute_eval_run(
    run_id: str, autorater_prompt: str, model: str, transcript_ids: list[str],
    eval_tags: list[str],
):
    """Execute the eval run: send each transcript through autorater, compute metrics.

    eval_tags: which tags to compute per-tag precision/recall for.
    Ground truth comes from each transcript's labels field:
    - labels[tag] == "P" → positive example (autorater should say "pass")
    - labels[tag] == "N" → negative example (autorater should say "fail")
    """
    db = await get_db()

    try:
        # Load transcripts with their labels
        transcripts = []
        for tid in transcript_ids:
            cursor = await db.execute("SELECT * FROM transcripts WHERE id = ?", (tid,))
            row = await cursor.fetchone()
            if row:
                labels = json.loads(row["labels"]) if row["labels"] else {}
                transcripts.append({
                    "id": row["id"],
                    "content": row["content"],
                    "labels": labels,
                })
    finally:
        await db.close()

    if not transcripts:
        db = await get_db()
        try:
            await db.execute(
                "UPDATE eval_runs SET status = 'failed', metrics = ? WHERE id = ?",
                (json.dumps({"error": "No transcripts found"}), run_id),
            )
            await db.commit()
        finally:
            await db.close()
        return

    # Process each transcript
    async def process_transcript(transcript):
        prompt = autorater_prompt.replace("{{transcript}}", transcript["content"])
        contents = gemini_client.build_contents([], user_message=prompt)
        try:
            result = await gemini_client.generate(
                system_prompt="You are an evaluation autorater. Respond with JSON only.",
                model=model,
                contents=contents,
            )
            text = result.get("text", "")
            predicted_labels = _parse_json_response(text)

            return {
                "transcript_id": transcript["id"],
                "predicted_labels": predicted_labels,
                "labels": transcript["labels"],
                "raw_response": result.get("raw_response"),
                "token_usage": result.get("token_usage"),
            }
        except Exception as e:
            return {
                "transcript_id": transcript["id"],
                "predicted_labels": {"error": str(e)},
                "labels": transcript["labels"],
                "raw_response": None,
                "token_usage": None,
            }

    results = await run_batch(transcripts, process_transcript)

    # Save results and compute metrics
    eval_results = []
    db = await get_db()
    try:
        for r in results:
            predicted = r["predicted_labels"]
            assessment = predicted.get("assessment") if isinstance(predicted, dict) else None
            labels = r["labels"]

            # ground_truth_labels: transcript's labels filtered to selected eval_tags
            ground_truth = {tag: labels[tag] for tag in eval_tags if tag in labels}

            result_id = str(uuid4())
            await db.execute(
                "INSERT INTO eval_results (id, run_id, transcript_id, predicted_labels, ground_truth_labels, match, raw_response, token_usage) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    result_id, run_id, r["transcript_id"],
                    json.dumps(predicted),
                    json.dumps(ground_truth),
                    None,  # match is no longer a single boolean
                    json.dumps(r["raw_response"]) if r["raw_response"] else None,
                    json.dumps(r["token_usage"]) if r["token_usage"] else None,
                ),
            )
            eval_results.append({
                "assessment": assessment,
                "labels": labels,
            })

        # Compute metrics
        total = len(eval_results)
        passed = sum(1 for r in eval_results if r.get("assessment") == "pass")
        pass_rate = passed / total if total > 0 else 0

        metrics = {
            "pass_rate": round(pass_rate, 4),
            "total": total,
            "passed": passed,
        }

        # Per-tag precision/recall when eval_tags provided
        if eval_tags:
            per_tag = {}
            for tag in eval_tags:
                tp = fp = fn = tn = 0
                for r in eval_results:
                    label = r["labels"].get(tag)
                    if label not in ("P", "N"):
                        continue  # not annotated for this tag
                    assessment = r.get("assessment")
                    if assessment == "pass" and label == "P":
                        tp += 1
                    elif assessment == "pass" and label == "N":
                        fp += 1
                    elif assessment == "fail" and label == "P":
                        fn += 1
                    elif assessment == "fail" and label == "N":
                        tn += 1

                annotated = tp + fp + fn + tn
                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

                per_tag[tag] = {
                    "precision": round(precision, 4),
                    "recall": round(recall, 4),
                    "f1": round(f1, 4),
                    "tp": tp,
                    "fp": fp,
                    "fn": fn,
                    "tn": tn,
                    "annotated": annotated,
                }
            metrics["per_tag"] = per_tag

        await db.execute(
            "UPDATE eval_runs SET status = 'completed', metrics = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (json.dumps(metrics), run_id),
        )
        await db.commit()
    except Exception as e:
        await db.execute(
            "UPDATE eval_runs SET status = 'failed', metrics = ? WHERE id = ?",
            (json.dumps({"error": str(e)}), run_id),
        )
        await db.commit()
    finally:
        await db.close()


def _parse_json_response(text: str) -> dict:
    """Try to parse JSON from Gemini response text."""
    import re
    # Try direct parse
    text = text.strip()
    # Remove markdown code blocks if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in text
        match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        return {"raw_text": text, "parse_error": "Could not parse JSON from response"}


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
        "eval_tags": json.loads(row["eval_tags"]) if row["eval_tags"] else None,
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
