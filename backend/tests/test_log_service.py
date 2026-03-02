"""Tests for the developer log service."""

import asyncio

import pytest

from app.services.log_service import LogService, LogEntry


def test_emit_creates_entry():
    service = LogService()
    entry = service.emit("REQ", "info", "GET /api/agents")
    assert isinstance(entry, LogEntry)
    assert entry.category == "REQ"
    assert entry.level == "info"
    assert entry.message == "GET /api/agents"
    assert entry.id  # uuid set
    assert entry.timestamp  # timestamp set


def test_emit_stores_in_buffer():
    service = LogService()
    service.emit("REQ", "info", "first")
    service.emit("RES", "info", "second")
    history = service.get_history()
    assert len(history) == 2
    assert history[0].message == "first"
    assert history[1].message == "second"


def test_buffer_capacity():
    service = LogService()
    # Fill beyond max (override for test)
    service._buffer = __import__("collections").deque(maxlen=5)
    for i in range(10):
        service.emit("REQ", "info", f"msg-{i}")
    history = service.get_history()
    assert len(history) == 5
    assert history[0].message == "msg-5"
    assert history[-1].message == "msg-9"


def test_emit_with_details():
    service = LogService()
    entry = service.emit("RES", "info", "200 OK", {"elapsed_ms": 42})
    assert entry.details == {"elapsed_ms": 42}


def test_to_dict():
    service = LogService()
    entry = service.emit("ERR", "error", "Something broke", {"code": 500})
    d = entry.to_dict()
    assert d["category"] == "ERR"
    assert d["level"] == "error"
    assert d["message"] == "Something broke"
    assert d["details"] == {"code": 500}
    assert "id" in d
    assert "timestamp" in d


@pytest.mark.asyncio
async def test_subscriber_receives_entries():
    service = LogService()
    queue = service.subscribe()
    assert service.subscriber_count == 1

    service.emit("REQ", "info", "test message")

    entry = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert entry.message == "test message"


@pytest.mark.asyncio
async def test_unsubscribe_removes_queue():
    service = LogService()
    queue = service.subscribe()
    assert service.subscriber_count == 1

    service.unsubscribe(queue)
    assert service.subscriber_count == 0

    # Emitting after unsubscribe should not fail
    service.emit("REQ", "info", "after unsubscribe")


@pytest.mark.asyncio
async def test_multiple_subscribers():
    service = LogService()
    q1 = service.subscribe()
    q2 = service.subscribe()
    assert service.subscriber_count == 2

    service.emit("REQ", "info", "broadcast")

    e1 = await asyncio.wait_for(q1.get(), timeout=1.0)
    e2 = await asyncio.wait_for(q2.get(), timeout=1.0)
    assert e1.message == "broadcast"
    assert e2.message == "broadcast"


@pytest.mark.asyncio
async def test_full_queue_does_not_block():
    service = LogService()
    queue = service.subscribe()

    # Fill the queue
    for i in range(200):
        service.emit("REQ", "info", f"msg-{i}")

    # Should not raise or block — some entries dropped
    assert queue.qsize() <= 100
