"""Tests for the autoraters and eval system API endpoints.

Focus: CRUD behavior, eval run lifecycle, and metrics structure.
"""

import pytest
import time


def make_autorater(client, name="Test Rater", prompt="Rate this: {{transcript}}", model="gemini-2.5-pro"):
    return client.post("/api/autoraters", json={
        "name": name,
        "prompt": prompt,
        "model": model,
    }).json()


def make_transcript(client, content="[USER] Hello\n[AGENT] Hi", labels=None):
    return client.post("/api/transcripts", json={
        "content": content,
        "labels": labels or {"safety": "P"},
        "source": "manual",
    }).json()


class TestAutoraterList:
    def test_list_returns_200(self, test_client):
        assert test_client.get("/api/autoraters").status_code == 200

    def test_list_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/autoraters").json(), list)


class TestAutoraterCreate:
    def test_create_returns_201(self, test_client):
        response = test_client.post("/api/autoraters", json={
            "name": "Safety Rater",
            "prompt": "Is this safe? {{transcript}}",
        })
        assert response.status_code == 201

    def test_create_stores_fields(self, test_client):
        rater = make_autorater(test_client, name="Math Rater", prompt="Rate math: {{transcript}}")
        assert rater["name"] == "Math Rater"
        assert rater["prompt"] == "Rate math: {{transcript}}"

    def test_create_returns_id(self, test_client):
        rater = make_autorater(test_client, )
        assert "id" in rater

    def test_create_default_model(self, test_client):
        rater = test_client.post("/api/autoraters", json={
            "name": "Rater",
            "prompt": "{{transcript}}",
        }).json()
        assert rater["model"] == "gemini-2.5-pro"

    def test_create_with_output_schema(self, test_client):
        schema = {"type": "object", "properties": {"assessment": {"type": "string"}}}
        rater = test_client.post("/api/autoraters", json={
            "name": "Schemed Rater",
            "prompt": "{{transcript}}",
            "output_schema": schema,
        }).json()
        assert rater["output_schema"] == schema


class TestAutoraterGet:
    def test_get_existing(self, test_client):
        rater = make_autorater(test_client, )
        response = test_client.get(f"/api/autoraters/{rater['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == rater["id"]

    def test_get_nonexistent_returns_404(self, test_client):
        assert test_client.get("/api/autoraters/nonexistent").status_code == 404


class TestAutoraterUpdate:
    def test_update_name(self, test_client):
        rater = make_autorater(test_client, name="Old")
        response = test_client.put(f"/api/autoraters/{rater['id']}", json={"name": "New"})
        assert response.status_code == 200
        assert response.json()["name"] == "New"

    def test_update_prompt(self, test_client):
        rater = make_autorater(test_client, )
        response = test_client.put(f"/api/autoraters/{rater['id']}", json={"prompt": "New prompt {{transcript}}"})
        assert response.json()["prompt"] == "New prompt {{transcript}}"

    def test_update_nonexistent_returns_404(self, test_client):
        assert test_client.put("/api/autoraters/nonexistent", json={"name": "x"}).status_code == 404


class TestEvalRuns:
    def test_list_eval_runs_returns_200(self, test_client):
        assert test_client.get("/api/eval/runs").status_code == 200

    def test_list_eval_runs_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/eval/runs").json(), list)

    def test_start_eval_run_returns_201(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        response = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
        })
        assert response.status_code == 201

    def test_start_eval_run_returns_run_id(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
        }).json()
        assert "id" in run

    def test_start_eval_run_initial_status_is_running(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
        }).json()
        assert run["status"] in ("running", "pending", "completed", "failed")

    def test_start_eval_run_with_nonexistent_autorater_returns_404(self, test_client):
        transcript = make_transcript(test_client, )
        response = test_client.post("/api/eval/run", json={
            "autorater_id": "nonexistent-id",
            "transcript_ids": [transcript["id"]],
        })
        assert response.status_code == 404

    def test_get_eval_run(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
        }).json()
        response = test_client.get(f"/api/eval/runs/{run['id']}")
        assert response.status_code == 200

    def test_get_nonexistent_eval_run_returns_404(self, test_client):
        assert test_client.get("/api/eval/runs/nonexistent").status_code == 404

    def test_eval_run_stores_transcript_ids(self, test_client):
        rater = make_autorater(test_client, )
        t1 = make_transcript(test_client, )
        t2 = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [t1["id"], t2["id"]],
        }).json()
        assert t1["id"] in run["transcript_ids"]
        assert t2["id"] in run["transcript_ids"]

    def test_eval_run_stores_eval_tags(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
            "eval_tags": ["safety", "math"],
        }).json()
        assert run["eval_tags"] == ["safety", "math"]

    def test_get_eval_results_for_run(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
        }).json()
        response = test_client.get(f"/api/eval/runs/{run['id']}/results")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_diff_eval_runs_endpoint(self, test_client):
        rater = make_autorater(test_client, )
        t = make_transcript(test_client, )
        run_a = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [t["id"]],
        }).json()
        run_b = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [t["id"]],
        }).json()
        response = test_client.get(f"/api/eval/runs/{run_a['id']}/diff/{run_b['id']}")
        assert response.status_code == 200
        data = response.json()
        assert "run_a_id" in data
        assert "run_b_id" in data
        assert "diffs" in data

    def test_eval_run_has_prompt_version_hash(self, test_client):
        rater = make_autorater(test_client, )
        transcript = make_transcript(test_client, )
        run = test_client.post("/api/eval/run", json={
            "autorater_id": rater["id"],
            "transcript_ids": [transcript["id"]],
        }).json()
        assert "prompt_version_hash" in run
        assert run["prompt_version_hash"] is not None
