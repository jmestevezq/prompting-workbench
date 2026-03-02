"""Tests for the devlogs SSE endpoint and HTTP logging middleware."""

from fastapi.testclient import TestClient
from app.main import app
from app.services.log_service import get_log_service


client = TestClient(app)


def test_devlogs_stream_content_type():
    """SSE endpoint should return text/event-stream content type."""
    with client.stream("GET", "/api/devlogs/stream") as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]


def test_devlogs_stream_receives_entries():
    """SSE endpoint should stream log entries as SSE data lines."""
    import json

    service = get_log_service()

    # Emit a log entry before connecting (goes to buffer)
    service.emit("REQ", "info", "test-sse-entry")

    with client.stream("GET", "/api/devlogs/stream") as response:
        # Read first few lines (buffer replay)
        found = False
        for line in response.iter_lines():
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if data.get("message") == "test-sse-entry":
                    found = True
                    assert data["category"] == "REQ"
                    assert data["level"] == "info"
                    break
        assert found, "Expected to find test-sse-entry in SSE stream"


def test_http_middleware_logs_requests(test_client):
    """HTTP middleware should log REQ/RES entries for regular endpoints."""
    service = get_log_service()

    # Clear existing buffer
    service._buffer.clear()

    # Make a request
    test_client.get("/health")

    history = service.get_history()
    messages = [e.message for e in history]

    # Should have REQ and RES entries for /health
    assert any("GET /health" in m for m in messages)
    assert any("200" in m and "/health" in m for m in messages)


def test_http_middleware_skips_devlogs_stream():
    """HTTP middleware should NOT log requests to /api/devlogs/stream."""
    service = get_log_service()
    service._buffer.clear()

    with client.stream("GET", "/api/devlogs/stream") as _:
        pass

    history = service.get_history()
    messages = [e.message for e in history]

    # Should NOT have REQ/RES entries for /api/devlogs/stream
    assert not any("/api/devlogs/stream" in m for m in messages)
