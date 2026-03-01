"""Tests for the agents API endpoints.

Focus: CRUD behavior, prompt versioning, and 404 handling.
"""

import pytest
import json


def make_agent(client, name="Test Agent", system_prompt="You are a test agent."):
    response = client.post("/api/agents", json={
        "name": name,
        "system_prompt": system_prompt,
        "model": "gemini-2.5-pro",
        "tool_definitions": [],
    })
    assert response.status_code == 201
    return response.json()


class TestAgentList:
    def test_list_returns_200(self, test_client):
        assert test_client.get("/api/agents").status_code == 200

    def test_list_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/agents").json(), list)


class TestAgentCreate:
    def test_create_returns_201(self, test_client):
        response = test_client.post("/api/agents", json={
            "name": "New Agent",
            "system_prompt": "You are helpful.",
        })
        assert response.status_code == 201

    def test_create_returns_agent_with_id(self, test_client):
        agent = make_agent(test_client)
        assert "id" in agent
        assert len(agent["id"]) > 0

    def test_create_stores_provided_fields(self, test_client):
        agent = make_agent(test_client, name="MyAgent", system_prompt="Be concise.")
        assert agent["name"] == "MyAgent"
        assert agent["system_prompt"] == "Be concise."

    def test_create_default_model(self, test_client):
        response = test_client.post("/api/agents", json={
            "name": "AgentX",
            "system_prompt": "Test",
        })
        agent = response.json()
        assert agent["model"] == "gemini-2.5-pro"

    def test_create_with_tool_definitions(self, test_client):
        tool_defs = [
            {"name": "myTool", "description": "Does stuff", "parameters": {"type": "OBJECT", "properties": {}}}
        ]
        response = test_client.post("/api/agents", json={
            "name": "ToolAgent",
            "system_prompt": "Use tools.",
            "tool_definitions": tool_defs,
        })
        assert response.status_code == 201
        assert response.json()["tool_definitions"] == tool_defs

    def test_create_timestamps_present(self, test_client):
        agent = make_agent(test_client)
        assert "created_at" in agent
        assert "updated_at" in agent


class TestAgentGet:
    def test_get_existing_agent(self, test_client):
        created = make_agent(test_client)
        response = test_client.get(f"/api/agents/{created['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == created["id"]

    def test_get_nonexistent_returns_404(self, test_client):
        assert test_client.get("/api/agents/nonexistent-id-12345").status_code == 404

    def test_get_returns_full_agent_fields(self, test_client):
        created = make_agent(test_client)
        agent = test_client.get(f"/api/agents/{created['id']}").json()
        assert "name" in agent
        assert "system_prompt" in agent
        assert "model" in agent
        assert "tool_definitions" in agent


class TestAgentUpdate:
    def test_update_name(self, test_client):
        agent = make_agent(test_client)
        response = test_client.put(f"/api/agents/{agent['id']}", json={"name": "Updated Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    def test_update_system_prompt(self, test_client):
        agent = make_agent(test_client)
        response = test_client.put(f"/api/agents/{agent['id']}", json={"system_prompt": "New prompt."})
        assert response.status_code == 200
        assert response.json()["system_prompt"] == "New prompt."

    def test_update_model(self, test_client):
        agent = make_agent(test_client)
        response = test_client.put(f"/api/agents/{agent['id']}", json={"model": "gemini-2.0-pro"})
        assert response.status_code == 200
        assert response.json()["model"] == "gemini-2.0-pro"

    def test_update_nonexistent_returns_404(self, test_client):
        response = test_client.put("/api/agents/nonexistent-id", json={"name": "x"})
        assert response.status_code == 404

    def test_partial_update_does_not_clear_other_fields(self, test_client):
        agent = make_agent(test_client, name="Original", system_prompt="Original prompt.")
        test_client.put(f"/api/agents/{agent['id']}", json={"name": "Changed"})
        updated = test_client.get(f"/api/agents/{agent['id']}").json()
        assert updated["system_prompt"] == "Original prompt."
        assert updated["name"] == "Changed"


class TestAgentDelete:
    def test_delete_returns_204(self, test_client):
        agent = make_agent(test_client)
        assert test_client.delete(f"/api/agents/{agent['id']}").status_code == 204

    def test_delete_removes_agent(self, test_client):
        agent = make_agent(test_client)
        test_client.delete(f"/api/agents/{agent['id']}")
        assert test_client.get(f"/api/agents/{agent['id']}").status_code == 404

    def test_delete_nonexistent_returns_404(self, test_client):
        assert test_client.delete("/api/agents/nonexistent-id").status_code == 404


class TestPromptVersions:
    def test_list_versions_empty_initially(self, test_client):
        agent = make_agent(test_client)
        response = test_client.get(f"/api/agents/{agent['id']}/versions")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_version_snapshots_current_prompt(self, test_client):
        agent = make_agent(test_client, system_prompt="Version 1 prompt.")
        response = test_client.post(f"/api/agents/{agent['id']}/versions", json={"label": "v1"})
        assert response.status_code == 201
        version = response.json()
        assert version["system_prompt"] == "Version 1 prompt."
        assert version["label"] == "v1"
        assert "version_hash" in version

    def test_create_version_generates_hash(self, test_client):
        agent = make_agent(test_client)
        version = test_client.post(f"/api/agents/{agent['id']}/versions", json={}).json()
        assert version["version_hash"] is not None
        assert len(version["version_hash"]) > 0

    def test_version_hash_changes_with_prompt(self, test_client):
        agent = make_agent(test_client, system_prompt="Prompt A")
        v1 = test_client.post(f"/api/agents/{agent['id']}/versions", json={}).json()
        test_client.put(f"/api/agents/{agent['id']}", json={"system_prompt": "Prompt B"})
        v2 = test_client.post(f"/api/agents/{agent['id']}/versions", json={}).json()
        assert v1["version_hash"] != v2["version_hash"]

    def test_list_versions_after_creating_one(self, test_client):
        agent = make_agent(test_client)
        test_client.post(f"/api/agents/{agent['id']}/versions", json={"label": "v1"})
        versions = test_client.get(f"/api/agents/{agent['id']}/versions").json()
        assert len(versions) >= 1

    def test_update_version_label(self, test_client):
        agent = make_agent(test_client)
        version = test_client.post(f"/api/agents/{agent['id']}/versions", json={"label": "initial"}).json()
        response = test_client.post(
            f"/api/agents/{agent['id']}/versions/{version['id']}/label",
            json={"label": "production-v2"},
        )
        assert response.status_code == 200
        assert response.json()["label"] == "production-v2"

    def test_version_has_agent_id(self, test_client):
        agent = make_agent(test_client)
        version = test_client.post(f"/api/agents/{agent['id']}/versions", json={}).json()
        assert version["agent_id"] == agent["id"]
