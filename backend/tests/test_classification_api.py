"""Tests for the classification evaluation API endpoints.

Focus: golden set management, prompt configuration, and run lifecycle.
"""

import pytest

SAMPLE_TRANSACTIONS = [{"merchant_name": "Whole Foods", "amount": 85.50}]
SAMPLE_EXPECTED = [{"merchant_name": "Whole Foods", "amount": 85.50, "category": "groceries"}]


def make_golden(client, set_name="test-set", input_tx=None, expected=None, tags=None):
    return client.post("/api/golden-sets", json={
        "set_name": set_name,
        "input_transactions": input_tx or SAMPLE_TRANSACTIONS,
        "expected_output": expected or SAMPLE_EXPECTED,
        "tags": tags or [],
    }).json()


def make_prompt(client, name="Test Prompt", template="Classify: {{input_transactions}}"):
    return client.post("/api/classification/prompts", json={
        "name": name,
        "prompt_template": template,
    }).json()


class TestGoldenSetList:
    def test_list_returns_200(self, test_client):
        assert test_client.get("/api/golden-sets").status_code == 200

    def test_list_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/golden-sets").json(), list)


class TestGoldenSetCreate:
    def test_create_returns_201(self, test_client):
        response = test_client.post("/api/golden-sets", json={
            "set_name": "my-set",
            "input_transactions": SAMPLE_TRANSACTIONS,
            "expected_output": SAMPLE_EXPECTED,
        })
        assert response.status_code == 201

    def test_create_stores_set_name(self, test_client):
        golden = make_golden(test_client, set_name="edge-cases")
        assert golden["set_name"] == "edge-cases"

    def test_create_stores_input_transactions(self, test_client):
        golden = make_golden(test_client, )
        assert golden["input_transactions"] == SAMPLE_TRANSACTIONS

    def test_create_stores_expected_output(self, test_client):
        golden = make_golden(test_client, )
        assert golden["expected_output"] == SAMPLE_EXPECTED

    def test_create_stores_tags(self, test_client):
        golden = make_golden(test_client, tags=["dedup", "edge-case"])
        assert "dedup" in golden["tags"]

    def test_create_with_reference_transactions(self, test_client):
        response = test_client.post("/api/golden-sets", json={
            "set_name": "ref-set",
            "input_transactions": SAMPLE_TRANSACTIONS,
            "expected_output": SAMPLE_EXPECTED,
            "reference_transactions": {"list_1": [], "list_2": [], "list_3": []},
        })
        assert response.status_code == 201

    def test_create_returns_id(self, test_client):
        golden = make_golden(test_client, )
        assert "id" in golden


class TestGoldenSetUpdate:
    def test_update_set_name(self, test_client):
        golden = make_golden(test_client, set_name="old")
        response = test_client.put(f"/api/golden-sets/{golden['id']}", json={"set_name": "new"})
        assert response.status_code == 200
        assert response.json()["set_name"] == "new"

    def test_update_expected_output(self, test_client):
        golden = make_golden(test_client, )
        new_expected = [{"category": "transportation"}]
        response = test_client.put(f"/api/golden-sets/{golden['id']}", json={"expected_output": new_expected})
        assert response.json()["expected_output"] == new_expected

    def test_update_nonexistent_returns_404(self, test_client):
        assert test_client.put("/api/golden-sets/nonexistent", json={"set_name": "x"}).status_code == 404


class TestGoldenSetImport:
    def test_import_single_item(self, test_client):
        response = test_client.post("/api/golden-sets/import", json={
            "items": [{
                "set_name": "imported-set",
                "input_transactions": SAMPLE_TRANSACTIONS,
                "expected_output": SAMPLE_EXPECTED,
            }]
        })
        assert response.status_code == 201
        assert len(response.json()) == 1

    def test_import_multiple_items(self, test_client):
        response = test_client.post("/api/golden-sets/import", json={
            "items": [
                {"set_name": "set-a", "input_transactions": [], "expected_output": []},
                {"set_name": "set-b", "input_transactions": [], "expected_output": []},
            ]
        })
        assert response.status_code == 201
        assert len(response.json()) == 2

    def test_imported_items_have_ids(self, test_client):
        response = test_client.post("/api/golden-sets/import", json={
            "items": [{"set_name": "s", "input_transactions": [], "expected_output": []}]
        })
        for item in response.json():
            assert "id" in item


class TestClassificationPromptList:
    def test_list_returns_200(self, test_client):
        assert test_client.get("/api/classification/prompts").status_code == 200

    def test_list_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/classification/prompts").json(), list)


class TestClassificationPromptCreate:
    def test_create_returns_201(self, test_client):
        response = test_client.post("/api/classification/prompts", json={
            "name": "My Prompt",
            "prompt_template": "Classify: {{input_transactions}}",
        })
        assert response.status_code == 201

    def test_create_stores_fields(self, test_client):
        prompt = make_prompt(test_client, name="Classifier", template="Classify: {{input_transactions}}")
        assert prompt["name"] == "Classifier"
        assert prompt["prompt_template"] == "Classify: {{input_transactions}}"

    def test_create_default_model(self, test_client):
        prompt = test_client.post("/api/classification/prompts", json={
            "name": "P",
            "prompt_template": "{{input_transactions}}",
        }).json()
        assert prompt["model"] == "gemini-2.5-pro"

    def test_create_returns_id(self, test_client):
        prompt = make_prompt(test_client, )
        assert "id" in prompt


class TestClassificationPromptUpdate:
    def test_update_name(self, test_client):
        prompt = make_prompt(test_client, name="Old")
        response = test_client.put(f"/api/classification/prompts/{prompt['id']}", json={"name": "New"})
        assert response.status_code == 200
        assert response.json()["name"] == "New"

    def test_update_template(self, test_client):
        prompt = make_prompt(test_client, )
        response = test_client.put(f"/api/classification/prompts/{prompt['id']}", json={
            "prompt_template": "New template {{input_transactions}}"
        })
        assert response.json()["prompt_template"] == "New template {{input_transactions}}"

    def test_update_nonexistent_returns_404(self, test_client):
        assert test_client.put("/api/classification/prompts/nonexistent", json={"name": "x"}).status_code == 404


class TestClassificationRuns:
    def test_list_runs_returns_200(self, test_client):
        assert test_client.get("/api/classification/runs").status_code == 200

    def test_list_runs_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/classification/runs").json(), list)

    def test_start_run_returns_201(self, test_client):
        prompt = make_prompt(test_client, )
        golden = make_golden(test_client, set_name="run-test-set")
        response = test_client.post("/api/classification/run", json={
            "prompt_id": prompt["id"],
            "golden_set_name": "run-test-set",
        })
        assert response.status_code == 201

    def test_start_run_with_nonexistent_prompt_returns_404(self, test_client):
        response = test_client.post("/api/classification/run", json={
            "prompt_id": "nonexistent",
            "golden_set_name": "any-set",
        })
        assert response.status_code == 404

    def test_get_run_returns_200(self, test_client):
        prompt = make_prompt(test_client, )
        golden = make_golden(test_client, set_name="get-run-set")
        run = test_client.post("/api/classification/run", json={
            "prompt_id": prompt["id"],
            "golden_set_name": "get-run-set",
        }).json()
        response = test_client.get(f"/api/classification/runs/{run['id']}")
        assert response.status_code == 200

    def test_get_nonexistent_run_returns_404(self, test_client):
        assert test_client.get("/api/classification/runs/nonexistent").status_code == 404

    def test_run_stores_prompt_id(self, test_client):
        prompt = make_prompt(test_client, )
        golden = make_golden(test_client, set_name="prompt-id-test-set")
        run = test_client.post("/api/classification/run", json={
            "prompt_id": prompt["id"],
            "golden_set_name": "prompt-id-test-set",
        }).json()
        assert run["prompt_id"] == prompt["id"]

    def test_run_stores_golden_set_name(self, test_client):
        prompt = make_prompt(test_client, )
        make_golden(test_client, set_name="golden-name-test-set")
        run = test_client.post("/api/classification/run", json={
            "prompt_id": prompt["id"],
            "golden_set_name": "golden-name-test-set",
        }).json()
        assert run["golden_set_name"] == "golden-name-test-set"

    def test_get_run_results(self, test_client):
        prompt = make_prompt(test_client, )
        make_golden(test_client, set_name="results-test-set")
        run = test_client.post("/api/classification/run", json={
            "prompt_id": prompt["id"],
            "golden_set_name": "results-test-set",
        }).json()
        response = test_client.get(f"/api/classification/runs/{run['id']}/results")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_run_has_prompt_version_hash(self, test_client):
        prompt = make_prompt(test_client, )
        make_golden(test_client, set_name="hash-test-set")
        run = test_client.post("/api/classification/run", json={
            "prompt_id": prompt["id"],
            "golden_set_name": "hash-test-set",
        }).json()
        assert "prompt_version_hash" in run
        assert run["prompt_version_hash"] is not None
