"""Generic async batch runner with semaphore-based concurrency."""

import asyncio
from typing import Any, Callable, Awaitable

from app.config import settings


async def run_batch(
    items: list[Any],
    process_fn: Callable[[Any], Awaitable[Any]],
    concurrency: int | None = None,
) -> list[Any]:
    """Run process_fn on each item with bounded concurrency.

    Args:
        items: List of items to process
        process_fn: Async function that processes one item
        concurrency: Max concurrent tasks (defaults to BATCH_CONCURRENCY setting)

    Returns:
        List of results in the same order as items
    """
    concurrency = concurrency or settings.BATCH_CONCURRENCY
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded_process(item):
        async with semaphore:
            return await process_fn(item)

    return await asyncio.gather(*[bounded_process(item) for item in items])
