"""SSE endpoint for streaming developer logs to the frontend."""

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.log_service import LogService, get_log_service

router = APIRouter(prefix="/api/devlogs", tags=["devlogs"])


async def _build_event_generator(service: LogService) -> AsyncGenerator[str, None]:
    """Async generator that yields SSE-formatted log entries.

    Replays buffer history first, then streams new entries indefinitely.
    Exported for unit testing.
    """
    queue = service.subscribe()
    try:
        # Replay buffer history
        for entry in service.get_history():
            yield f"data: {json.dumps(entry.to_dict())}\n\n"

        # Stream new entries as they arrive
        while True:
            try:
                entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield f"data: {json.dumps(entry.to_dict())}\n\n"
            except asyncio.TimeoutError:
                # Keepalive comment to prevent proxy/browser timeouts
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        service.unsubscribe(queue)


@router.get("/stream")
async def stream_logs():
    """Server-Sent Events endpoint for real-time developer logs."""
    service = get_log_service()
    return StreamingResponse(
        _build_event_generator(service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
