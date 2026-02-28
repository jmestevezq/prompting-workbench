"""Tests for the transcripts API endpoints.

Focus: CRUD behavior, import, filtering, and label management.
"""

import pytest


def make_transcript(client, name="Test", content="[USER] Hi\n[AGENT] Hello", labels=None, source="manual", tags=None):
    return client.post("/api/transcripts", json={
        "name": name,
        "content": content,
        "labels": labels or {},
        "source": source,
        "tags": tags or [],
    }).json()


class TestTranscriptList:
    def test_list_returns_200(self, test_client):
        assert test_client.get("/api/transcripts").status_code == 200

    def test_list_returns_array(self, test_client):
        assert isinstance(test_client.get("/api/transcripts").json(), list)

    def test_filter_by_source(self, test_client):
        make_transcript(test_client, name="ManualTx", source="manual")
        make_transcript(test_client, name="GeneratedTx", source="generated")
        response = test_client.get("/api/transcripts?source=generated")
        results = response.json()
        for r in results:
            assert r["source"] == "generated"

    def test_filter_by_tag(self, test_client):
        make_transcript(test_client, name="Tagged", tags=["safety", "math"])
        make_transcript(test_client, name="Untagged", tags=[])
        results = test_client.get("/api/transcripts?tag=safety").json()
        for r in results:
            assert "safety" in (r.get("tags") or [])


class TestTranscriptCreate:
    def test_create_returns_201(self, test_client):
        response = test_client.post("/api/transcripts", json={
            "name": "My Transcript",
            "content": "[USER] Hello\n[AGENT] Hi",
            "labels": {},
        })
        assert response.status_code == 201

    def test_create_returns_id(self, test_client):
        t = make_transcript(test_client, )
        assert "id" in t

    def test_create_stores_content(self, test_client):
        content = "[USER] Special content\n[AGENT] Response"
        t = make_transcript(test_client, content=content)
        assert t["content"] == content

    def test_create_stores_labels(self, test_client):
        labels = {"safety": "pass", "math": "fail"}
        t = make_transcript(test_client, labels=labels)
        assert t["labels"] == labels

    def test_create_stores_tags(self, test_client):
        tags = ["safety-issue", "math-error"]
        t = make_transcript(test_client, tags=tags)
        assert t["tags"] == tags

    def test_create_stores_source(self, test_client):
        t = make_transcript(test_client, source="generated")
        assert t["source"] == "generated"

    def test_create_with_empty_labels(self, test_client):
        t = make_transcript(test_client, labels={})
        assert t["labels"] == {}

    def test_create_with_parsed_turns(self, test_client):
        parsed_turns = [{"role": "user", "content": "Hello"}]
        response = test_client.post("/api/transcripts", json={
            "content": "[USER] Hello",
            "labels": {},
            "parsed_turns": parsed_turns,
        })
        assert response.status_code == 201
        assert response.json()["parsed_turns"] == parsed_turns


class TestTranscriptGet:
    def test_get_existing(self, test_client):
        t = make_transcript(test_client, )
        response = test_client.get(f"/api/transcripts/{t['id']}")
        assert response.status_code == 200
        assert response.json()["id"] == t["id"]

    def test_get_nonexistent_returns_404(self, test_client):
        assert test_client.get("/api/transcripts/nonexistent").status_code == 404


class TestTranscriptUpdate:
    def test_update_content(self, test_client):
        t = make_transcript(test_client, )
        response = test_client.put(f"/api/transcripts/{t['id']}", json={"content": "Updated content"})
        assert response.status_code == 200
        assert response.json()["content"] == "Updated content"

    def test_update_labels(self, test_client):
        t = make_transcript(test_client, labels={"safety": "fail"})
        response = test_client.put(f"/api/transcripts/{t['id']}", json={"labels": {"safety": "pass"}})
        assert response.json()["labels"]["safety"] == "pass"

    def test_update_tags(self, test_client):
        t = make_transcript(test_client, tags=["old-tag"])
        response = test_client.put(f"/api/transcripts/{t['id']}", json={"tags": ["new-tag"]})
        assert response.json()["tags"] == ["new-tag"]

    def test_update_name(self, test_client):
        t = make_transcript(test_client, name="Old")
        response = test_client.put(f"/api/transcripts/{t['id']}", json={"name": "New"})
        assert response.json()["name"] == "New"

    def test_update_nonexistent_returns_404(self, test_client):
        assert test_client.put("/api/transcripts/nonexistent", json={"name": "x"}).status_code == 404

    def test_partial_update_preserves_other_fields(self, test_client):
        t = make_transcript(test_client, name="Original", labels={"safety": "pass"})
        test_client.put(f"/api/transcripts/{t['id']}", json={"name": "Updated"})
        result = test_client.get(f"/api/transcripts/{t['id']}").json()
        assert result["labels"]["safety"] == "pass"


class TestTranscriptDelete:
    def test_delete_returns_204(self, test_client):
        t = make_transcript(test_client, )
        assert test_client.delete(f"/api/transcripts/{t['id']}").status_code == 204

    def test_deleted_transcript_not_found(self, test_client):
        t = make_transcript(test_client, )
        test_client.delete(f"/api/transcripts/{t['id']}")
        assert test_client.get(f"/api/transcripts/{t['id']}").status_code == 404

    def test_delete_nonexistent_returns_404(self, test_client):
        assert test_client.delete("/api/transcripts/nonexistent").status_code == 404


class TestTranscriptImport:
    def test_import_single_transcript(self, test_client):
        response = test_client.post("/api/transcripts/import", json={
            "transcripts": [
                {"content": "[USER] Hello", "labels": {"safety": "pass"}, "source": "imported"}
            ]
        })
        assert response.status_code == 201
        assert len(response.json()) == 1

    def test_import_multiple_transcripts(self, test_client):
        response = test_client.post("/api/transcripts/import", json={
            "transcripts": [
                {"content": "[USER] A", "labels": {}, "source": "imported"},
                {"content": "[USER] B", "labels": {}, "source": "imported"},
                {"content": "[USER] C", "labels": {}, "source": "imported"},
            ]
        })
        assert response.status_code == 201
        assert len(response.json()) == 3

    def test_imported_transcripts_have_ids(self, test_client):
        response = test_client.post("/api/transcripts/import", json={
            "transcripts": [{"content": "[USER] Hi", "labels": {}}]
        })
        for t in response.json():
            assert "id" in t

    def test_import_with_labels(self, test_client):
        response = test_client.post("/api/transcripts/import", json={
            "transcripts": [
                {"content": "[USER] Test", "labels": {"safety": "fail"}, "tags": ["safety-issue"]}
            ]
        })
        result = response.json()[0]
        assert result["labels"]["safety"] == "fail"
        assert "safety-issue" in result["tags"]
