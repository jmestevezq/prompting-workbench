"""Tests for the settings API endpoints.

Focus: reading settings, updating settings, and validation behavior.
"""

import pytest


class TestGetSettings:
    def test_get_settings_returns_200(self, test_client):
        response = test_client.get("/api/settings")
        assert response.status_code == 200

    def test_get_settings_has_required_fields(self, test_client):
        data = test_client.get("/api/settings").json()
        assert "has_api_key" in data
        assert "default_model" in data
        assert "batch_concurrency" in data
        assert "code_execution_timeout" in data

    def test_has_api_key_is_boolean(self, test_client):
        data = test_client.get("/api/settings").json()
        assert isinstance(data["has_api_key"], bool)

    def test_batch_concurrency_is_integer(self, test_client):
        data = test_client.get("/api/settings").json()
        assert isinstance(data["batch_concurrency"], int)

    def test_code_execution_timeout_is_integer(self, test_client):
        data = test_client.get("/api/settings").json()
        assert isinstance(data["code_execution_timeout"], int)

    def test_default_model_is_string(self, test_client):
        data = test_client.get("/api/settings").json()
        assert isinstance(data["default_model"], str)


class TestUpdateSettings:
    def test_update_default_model(self, test_client):
        test_client.put("/api/settings", json={"default_model": "gemini-2.0-pro"})
        data = test_client.get("/api/settings").json()
        assert data["default_model"] == "gemini-2.0-pro"
        # Restore
        test_client.put("/api/settings", json={"default_model": "gemini-2.5-pro"})

    def test_update_batch_concurrency(self, test_client):
        test_client.put("/api/settings", json={"batch_concurrency": 10})
        data = test_client.get("/api/settings").json()
        assert data["batch_concurrency"] == 10
        # Restore
        test_client.put("/api/settings", json={"batch_concurrency": 5})

    def test_update_code_execution_timeout(self, test_client):
        test_client.put("/api/settings", json={"code_execution_timeout": 30})
        data = test_client.get("/api/settings").json()
        assert data["code_execution_timeout"] == 30
        # Restore
        test_client.put("/api/settings", json={"code_execution_timeout": 10})

    def test_update_api_key_reflects_has_api_key_true(self, test_client):
        test_client.put("/api/settings", json={"gemini_api_key": "real-api-key-123"})
        data = test_client.get("/api/settings").json()
        assert data["has_api_key"] is True

    def test_placeholder_api_key_reflects_has_api_key_false(self, test_client):
        test_client.put("/api/settings", json={"gemini_api_key": "your-api-key-here"})
        data = test_client.get("/api/settings").json()
        assert data["has_api_key"] is False

    def test_partial_update_does_not_clear_other_settings(self, test_client):
        # Set a known state
        test_client.put("/api/settings", json={"batch_concurrency": 7})
        # Update only the model
        test_client.put("/api/settings", json={"default_model": "gemini-2.0-pro"})
        data = test_client.get("/api/settings").json()
        assert data["batch_concurrency"] == 7
        # Restore
        test_client.put("/api/settings", json={"default_model": "gemini-2.5-pro", "batch_concurrency": 5})

    def test_update_returns_updated_settings(self, test_client):
        response = test_client.put("/api/settings", json={"batch_concurrency": 8})
        assert response.status_code == 200
        assert response.json()["batch_concurrency"] == 8
        # Restore
        test_client.put("/api/settings", json={"batch_concurrency": 5})
