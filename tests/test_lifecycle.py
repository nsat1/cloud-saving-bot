import asyncio
from unittest.mock import AsyncMock

from app.middlewares.lifecycle import InFlightMiddleware


async def test_drain_waits_for_active_handler_to_finish():
    lifecycle = InFlightMiddleware()
    entered = asyncio.Event()
    release = asyncio.Event()

    async def handler(event, data):
        entered.set()
        await release.wait()
        return "finished"

    task = asyncio.create_task(lifecycle(handler, None, {}))
    await entered.wait()
    drain = asyncio.create_task(lifecycle.drain(1))
    await asyncio.sleep(0)
    assert not drain.done()
    release.set()
    assert await task == "finished"
    await drain
    blocked = AsyncMock()
    await lifecycle(blocked, None, {})
    blocked.assert_not_awaited()


async def test_drain_cancels_handler_after_grace_period():
    lifecycle = InFlightMiddleware()
    entered = asyncio.Event()
    cleaned = asyncio.Event()

    async def handler(event, data):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cleaned.set()

    task = asyncio.create_task(lifecycle(handler, None, {}))
    await entered.wait()
    await lifecycle.drain(0)
    assert task.cancelled()
    assert cleaned.is_set()
