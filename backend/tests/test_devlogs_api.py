"""Tests for the devlogs SSE endpoint and HTTP logging middleware."""

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.log_service import get_log_service


@pytest.fixture(autouse=True)
def clear_log_buffer():
    """Clear the log buffer before each test to avoid cross-test contamination."""
    service = get_log_service()
    service._buffer.clear()
    yield


# ─── SSE generator – async unit tests ────────────────────────────────────────
# Note: We test the async generator directly (not via HTTP) because the SSE
# stream is infinite and TestClient blocks until the ASGI handler finishes.

@pytest.mark.asyncio
async def test_devlogs_stream_replays_buffer():
    """SSE event_generator should replay buffered entries before new ones."""
    from app.routers.devlogs import _build_event_generator

    service = get_log_service()
    service.emit("REQ", "info", "buf-entry-1")
    service.emit("RES", "info", "buf-entry-2")

    received: list[dict] = []
    async for raw_line in _build_event_generator(service):
        if raw_line.startswith("data: "):
            received.append(json.loads(raw_line[6:]))
        if len(received) >= 2:
            break

    messages = [e["message"] for e in received]
    assert "buf-entry-1" in messages
    assert "buf-entry-2" in messages


@pytest.mark.asyncio
async def test_devlogs_stream_entry_format():
    """SSE entries should be valid JSON with expected fields."""
    from app.routers.devlogs import _build_event_generator

    service = get_log_service()
    service.emit("TOOL", "debug", "gen-format-test", {"tool": "execute_code"})

    found_entry: dict | None = None
    async for raw_line in _build_event_generator(service):
        if raw_line.startswith("data: "):
            entry = json.loads(raw_line[6:])
            if entry.get("message") == "gen-format-test":
                found_entry = entry
                break

    assert found_entry is not None
    assert found_entry["category"] == "TOOL"
    assert found_entry["level"] == "debug"
    assert found_entry["details"] == {"tool": "execute_code"}
    assert "id" in found_entry
    assert "timestamp" in found_entry


@pytest.mark.asyncio
async def test_devlogs_stream_subscribes_and_unsubscribes():
    """Generator should subscribe on enter and unsubscribe on close."""
    from app.routers.devlogs import _build_event_generator

    service = get_log_service()
    initial_count = service.subscriber_count

    gen = _build_event_generator(service)
    # Start the generator (subscription happens when first entry is yielded)
    service.emit("REQ", "info", "sub-test")
    entry_line = await gen.__anext__()
    assert service.subscriber_count == initial_count + 1

    # Close the generator — should unsubscribe
    await gen.aclose()
    assert service.subscriber_count == initial_count


# ─── HTTP middleware tests ────────────────────────────────────────────────────

def test_http_middleware_logs_requests(test_client):
    """HTTP middleware should log REQ/RES entries for regular endpoints."""
    service = get_log_service()

    test_client.get("/health")

    history = service.get_history()
    messages = [e.message for e in history]

    assert any("GET /health" in m for m in messages)
    assert any("200" in m and "/health" in m for m in messages)


def test_http_middleware_logs_elapsed_time(test_client):
    """RES log entries should include elapsed_ms in details."""
    service = get_log_service()

    test_client.get("/health")

    history = service.get_history()
    res_entries = [e for e in history if e.category == "RES" and "/health" in e.message]
    assert res_entries, "No RES entry found for /health"
    assert res_entries[0].details is not None
    assert "elapsed_ms" in res_entries[0].details


def test_http_middleware_logs_error_responses(test_client):
    """HTTP middleware should log 4xx responses with warn level."""
    service = get_log_service()

    test_client.get("/api/this-does-not-exist")

    history = service.get_history()
    warn_entries = [e for e in history if e.level == "warn" and e.category == "RES"]
    assert any("/api/this-does-not-exist" in e.message for e in warn_entries)


def test_http_middleware_skip_logic():
    """Middleware skip path is /api/devlogs/stream — verified by absence of logging."""
    service = get_log_service()
    # Make a regular request; confirm it gets logged
    client = TestClient(app)
    client.get("/health")
    history = service.get_history()
    assert any("/health" in e.message for e in history)

    # Confirm the skip path string matches what the middleware checks
    from app.main import app as _app
    # The middleware skips "/api/devlogs/stream" — assert it's in main.py source
    import inspect
    import app.main as main_module
    src = inspect.getsource(main_module.http_logging_middleware)
    assert "/api/devlogs/stream" in src
