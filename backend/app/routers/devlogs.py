"""SSE endpoint for streaming developer logs to the frontend."""

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.log_service import get_log_service

router = APIRouter(prefix="/api/devlogs", tags=["devlogs"])


@router.get("/stream")
async def stream_logs():
    """Server-Sent Events endpoint for real-time developer logs."""
    service = get_log_service()

    async def event_generator():
        queue = service.subscribe()
        try:
            # Replay buffer history
            for entry in service.get_history():
                yield f"data: {json.dumps(entry.to_dict())}\n\n"

            # Stream new entries
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(entry.to_dict())}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive comment to prevent connection timeout
                    yield ": keepalive\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            service.unsubscribe(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
