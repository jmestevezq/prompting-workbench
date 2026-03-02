"""Developer log service — ring buffer + SSE subscriber queues.

Provides a simple singleton that captures log entries for real-time
streaming to the frontend via Server-Sent Events.
"""

import asyncio
from collections import deque
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

# Categories: REQ, RES, DB, GEMINI, TOOL, WS, ERR
# Levels: info, warn, error, debug

MAX_BUFFER_SIZE = 1000
MAX_SUBSCRIBER_QUEUE_SIZE = 100


@dataclass
class LogEntry:
    id: str
    timestamp: str
    category: str
    level: str
    message: str
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class LogService:
    """Singleton log service with ring buffer and subscriber queues."""

    def __init__(self):
        self._buffer: deque[LogEntry] = deque(maxlen=MAX_BUFFER_SIZE)
        self._subscribers: set[asyncio.Queue[LogEntry]] = set()

    def emit(self, category: str, level: str, message: str, details: dict[str, Any] | None = None) -> LogEntry:
        entry = LogEntry(
            id=str(uuid4()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            category=category,
            level=level,
            message=message,
            details=details,
        )
        self._buffer.append(entry)
        for queue in self._subscribers:
            try:
                queue.put_nowait(entry)
            except asyncio.QueueFull:
                pass  # Drop if subscriber is slow — never block
        return entry

    def subscribe(self) -> asyncio.Queue[LogEntry]:
        queue: asyncio.Queue[LogEntry] = asyncio.Queue(maxsize=MAX_SUBSCRIBER_QUEUE_SIZE)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[LogEntry]) -> None:
        self._subscribers.discard(queue)

    def get_history(self) -> list[LogEntry]:
        return list(self._buffer)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# Module-level singleton
_service = LogService()


def dev_log(category: str, level: str, message: str, details: dict[str, Any] | None = None) -> LogEntry:
    """Convenience function to emit a log entry."""
    return _service.emit(category, level, message, details)


def get_log_service() -> LogService:
    """Get the singleton log service instance."""
    return _service
