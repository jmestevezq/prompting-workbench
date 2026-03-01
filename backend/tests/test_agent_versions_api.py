"""Tests for agent version and import API endpoints."""

import json
import pytest
from pathlib import Path


class TestImportAgent:
    def test_import_sherlock_finance(self, test_client):
        """Import the sherlock-finance agent from files."""
        resp = test_client.post("/api/agents/import/sherlock-finance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Sherlock Finance Assistant"
        assert "Base (2.0)" in data["version_label"]
        assert data["message"] == "Agent imported successfully"
        assert data["agent_id"]
        assert data["version_id"]

    def test_import_creates_agent_record(self, test_client):
        resp = test_client.post("/api/agents/import/sherlock-finance")
        agent_id = resp.json()["agent_id"]

        agent_resp = test_client.get(f"/api/agents/{agent_id}")
        assert agent_resp.status_code == 200
        agent = agent_resp.json()
        assert agent["name"] == "Sherlock Finance Assistant"
        assert agent["agent_folder"] == "sherlock-finance"
        assert agent["active_version_id"] is not None

    def test_import_creates_version_record(self, test_client):
        resp = test_client.post("/api/agents/import/sherlock-finance")
        agent_id = resp.json()["agent_id"]

        versions_resp = test_client.get(f"/api/agents/{agent_id}/agent-versions")
        assert versions_resp.status_code == 200
        versions = versions_resp.json()
        assert len(versions) == 1
        v = versions[0]
        assert v["is_base"] is True
        assert v["source"] == "file"
        assert "financial assistant" in v["system_prompt"].lower()
        assert v["raw_template"] is not None
        assert "${model.currentDate}" in v["raw_template"]

    def test_reimport_updates_base_version(self, test_client):
        # First import
        resp1 = test_client.post("/api/agents/import/sherlock-finance")
        agent_id = resp1.json()["agent_id"]
        version_id = resp1.json()["version_id"]

        # Re-import
        resp2 = test_client.post("/api/agents/import/sherlock-finance")
        assert resp2.status_code == 200
        assert resp2.json()["agent_id"] == agent_id
        assert resp2.json()["version_id"] == version_id
        assert resp2.json()["message"] == "Agent re-imported successfully"

        # Should still have just 1 version
        versions = test_client.get(f"/api/agents/{agent_id}/agent-versions").json()
        assert len(versions) == 1

    def test_import_nonexistent_folder(self, test_client):
        resp = test_client.post("/api/agents/import/nonexistent-agent")
        assert resp.status_code == 400

    def test_rendered_prompt_in_version(self, test_client):
        resp = test_client.post("/api/agents/import/sherlock-finance")
        agent_id = resp.json()["agent_id"]
        versions = test_client.get(f"/api/agents/{agent_id}/agent-versions").json()
        prompt = versions[0]["system_prompt"]
        # Check that template was rendered (no FreeMarker directives remain)
        assert "${" not in prompt
        assert "<#" not in prompt
        assert "financial assistant" in prompt.lower()


class TestAgentVersionCRUD:
    def _create_agent(self, client):
        resp = client.post("/api/agents", json={
            "name": "Test Agent",
            "system_prompt": "You are a test agent.",
            "model": "gemini-2.5-pro",
            "tool_definitions": [],
        })
        return resp.json()["id"]

    def test_create_version(self, test_client):
        agent_id = self._create_agent(test_client)
        resp = test_client.post(f"/api/agents/{agent_id}/agent-versions", json={
            "version_label": "v1.1 - tweaked",
            "system_prompt": "You are an updated test agent.",
        })
        assert resp.status_code == 201
        v = resp.json()
        assert v["version_label"] == "v1.1 - tweaked"
        assert v["source"] == "ui"
        assert v["is_base"] is False
        assert v["system_prompt"] == "You are an updated test agent."

    def test_list_versions(self, test_client):
        agent_id = self._create_agent(test_client)
        test_client.post(f"/api/agents/{agent_id}/agent-versions", json={
            "version_label": "v1",
            "system_prompt": "Prompt v1",
        })
        test_client.post(f"/api/agents/{agent_id}/agent-versions", json={
            "version_label": "v2",
            "system_prompt": "Prompt v2",
        })
        resp = test_client.get(f"/api/agents/{agent_id}/agent-versions")
        assert resp.status_code == 200
        versions = resp.json()
        assert len(versions) == 2

    def test_create_version_nonexistent_agent(self, test_client):
        resp = test_client.post("/api/agents/nonexistent/agent-versions", json={
            "version_label": "v1",
            "system_prompt": "test",
        })
        assert resp.status_code == 404


class TestActiveVersion:
    def _import_agent(self, client):
        resp = client.post("/api/agents/import/sherlock-finance")
        return resp.json()["agent_id"], resp.json()["version_id"]

    def test_set_active_version(self, test_client):
        agent_id, version_id = self._import_agent(test_client)

        # Create a new version
        new_version_resp = test_client.post(f"/api/agents/{agent_id}/agent-versions", json={
            "version_label": "v2",
            "system_prompt": "New prompt",
        })
        new_version_id = new_version_resp.json()["id"]

        # Switch active version
        resp = test_client.put(
            f"/api/agents/{agent_id}/active-version?version_id={new_version_id}"
        )
        assert resp.status_code == 200
        assert resp.json()["active_version_id"] == new_version_id

    def test_set_active_version_nonexistent(self, test_client):
        agent_id, _ = self._import_agent(test_client)
        resp = test_client.put(
            f"/api/agents/{agent_id}/active-version?version_id=nonexistent"
        )
        assert resp.status_code == 404


class TestAgentTemplate:
    def test_get_template_with_active_version(self, test_client):
        resp = test_client.post("/api/agents/import/sherlock-finance")
        agent_id = resp.json()["agent_id"]

        tmpl_resp = test_client.get(f"/api/agents/{agent_id}/template")
        assert tmpl_resp.status_code == 200
        tmpl = tmpl_resp.json()
        assert tmpl["raw_template"] is not None
        assert "${model.currentDate}" in tmpl["raw_template"]
        assert tmpl["variables"] is not None
        assert tmpl["system_prompt"] is not None
        assert "financial assistant" in tmpl["system_prompt"].lower()

    def test_get_template_without_version(self, test_client):
        # Create a regular agent (no import)
        resp = test_client.post("/api/agents", json={
            "name": "Plain Agent",
            "system_prompt": "Plain prompt",
            "tool_definitions": [],
        })
        agent_id = resp.json()["id"]

        tmpl_resp = test_client.get(f"/api/agents/{agent_id}/template")
        assert tmpl_resp.status_code == 200
        tmpl = tmpl_resp.json()
        assert tmpl["raw_template"] is None
        assert tmpl["system_prompt"] == "Plain prompt"


class TestListFolders:
    def test_list_available_folders(self, test_client):
        resp = test_client.get("/api/agents/folders/available")
        assert resp.status_code == 200
        folders = resp.json()["folders"]
        assert "sherlock-finance" in folders
