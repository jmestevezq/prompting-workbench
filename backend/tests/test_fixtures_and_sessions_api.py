"""Tests for the fixtures and sessions API endpoints.

Focus: CRUD behavior, data integrity, and relationships between resources.
"""

import pytest


def make_agent(client):
    return client.post("/api/agents", json={
        "name": "Agent",
        "system_prompt": "You are helpful.",
    }).json()


def make_fixture(client, name="Test Fixture", type_="transactions", data=None):
    if data is None:
        data = [{"merchant_name": "Store", "amount": 50, "category": "food"}]
    return client.post("/api/fixtures", json={
        "name": name,
        "type": type_,
        "data": data,
    }).json()


class TestFixtureList:
    def test_list_returns_200(self, test_client):
        assert test_client.get("/api/fixtures").status_code == 200

    def test_list_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/fixtures").json(), list)


class TestFixtureCreate:
    def test_create_returns_201(self, test_client):
        response = test_client.post("/api/fixtures", json={
            "name": "User Profile",
            "type": "user_profile",
            "data": {"name": "Jane"},
        })
        assert response.status_code == 201

    def test_create_stores_provided_fields(self, test_client):
        fixture = make_fixture(test_client, name="My Fixture", type_="transactions")
        assert fixture["name"] == "My Fixture"
        assert fixture["type"] == "transactions"

    def test_create_returns_id(self, test_client):
        fixture = make_fixture(test_client, )
        assert "id" in fixture
        assert len(fixture["id"]) > 0

    def test_create_stores_json_data(self, test_client):
        data = [{"merchant_name": "Amazon", "amount": 99.99, "category": "shopping"}]
        fixture = make_fixture(test_client, data=data)
        assert fixture["data"] == data

    def test_create_user_profile_fixture(self, test_client):
        profile = {"name": "Jane Doe", "monthly_budget": 3000}
        fixture = make_fixture(test_client, type_="user_profile", data=profile)
        assert fixture["type"] == "user_profile"
        assert fixture["data"]["name"] == "Jane Doe"


class TestFixtureGet:
    def test_get_existing_fixture(self, test_client):
        fixture = make_fixture(test_client, )
        response = test_client.get(f"/api/fixtures/{fixture['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == fixture["id"]

    def test_get_nonexistent_returns_404(self, test_client):
        response = test_client.get("/api/fixtures/nonexistent-id")
        assert response.status_code == 404


class TestFixtureUpdate:
    def test_update_name(self, test_client):
        fixture = make_fixture(test_client, name="Old Name")
        response = test_client.put(f"/api/fixtures/{fixture['id']}", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"

    def test_update_data(self, test_client):
        fixture = make_fixture(test_client, )
        new_data = [{"merchant_name": "Walmart", "amount": 30, "category": "groceries"}]
        response = test_client.put(f"/api/fixtures/{fixture['id']}", json={"data": new_data})
        assert response.status_code == 200
        assert response.json()["data"] == new_data

    def test_update_nonexistent_returns_404(self, test_client):
        response = test_client.put("/api/fixtures/nonexistent-id", json={"name": "x"})
        assert response.status_code == 404


class TestFixtureDelete:
    def test_delete_returns_204(self, test_client):
        fixture = make_fixture(test_client, )
        assert test_client.delete(f"/api/fixtures/{fixture['id']}").status_code == 204

    def test_deleted_fixture_not_found(self, test_client):
        fixture = make_fixture(test_client, )
        test_client.delete(f"/api/fixtures/{fixture['id']}")
        assert test_client.get(f"/api/fixtures/{fixture['id']}").status_code == 404

    def test_delete_nonexistent_returns_404(self, test_client):
        assert test_client.delete("/api/fixtures/nonexistent-id").status_code == 404


class TestSessionCreate:
    def test_create_session_returns_201(self, test_client):
        agent = make_agent(test_client)
        response = test_client.post("/api/sessions", json={"agent_id": agent["id"]})
        assert response.status_code == 201

    def test_create_session_with_fixtures(self, test_client):
        agent = make_agent(test_client)
        fixture = make_fixture(test_client, )
        response = test_client.post("/api/sessions", json={
            "agent_id": agent["id"],
            "fixture_ids": [fixture["id"]],
        })
        assert response.status_code == 201
        session = response.json()
        assert fixture["id"] in session["fixture_ids"]

    def test_create_session_returns_id(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        assert "id" in session

    def test_create_session_links_agent(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        assert session["agent_id"] == agent["id"]

    def test_create_session_without_fixtures(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        assert session["fixture_ids"] == [] or session["fixture_ids"] is None or len(session["fixture_ids"]) == 0


class TestSessionGet:
    def test_get_existing_session(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        response = test_client.get(f"/api/sessions/{session['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == session["id"]

    def test_get_nonexistent_session_returns_404(self, test_client):
        assert test_client.get("/api/sessions/nonexistent-id").status_code == 404


class TestSessionTurns:
    def test_new_session_has_no_turns(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        turns = test_client.get(f"/api/sessions/{session['id']}/turns").json()
        assert isinstance(turns, list)
        assert len(turns) == 0

    def test_list_turns_default_active_only(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        response = test_client.get(f"/api/sessions/{session['id']}/turns")
        assert response.status_code == 200

    def test_list_turns_with_active_only_false(self, test_client):
        agent = make_agent(test_client)
        session = test_client.post("/api/sessions", json={"agent_id": agent["id"]}).json()
        response = test_client.get(f"/api/sessions/{session['id']}/turns?active_only=false")
        assert response.status_code == 200


class TestSessionList:
    def test_list_sessions_returns_200(self, test_client):
        assert test_client.get("/api/sessions").status_code == 200

    def test_list_sessions_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/sessions").json(), list)
