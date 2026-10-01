"""Ожидание завершения активных обработчиков перед закрытием клиентских сессий."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

logger = logging.getLogger(__name__)


class InFlightMiddleware(BaseMiddleware):
    def __init__(self) -> None:
        self._tasks: set[asyncio.Task[Any]] = set()
        self._stopping = False

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if self._stopping:
            return None
        task = asyncio.current_task()
        if task is None:
            raise RuntimeError("Handler must run inside an asyncio task")
        self._tasks.add(task)
        try:
            return await handler(event, data)
        finally:
            self._tasks.discard(task)

    async def drain(self, grace_period: float) -> None:
        self._stopping = True
        tasks = self._tasks - {asyncio.current_task()}
        if not tasks:
            return
        _, pending = await asyncio.wait(tasks, timeout=grace_period)
        if pending:
            logger.warning("Shutdown timeout: cancelling %s active handlers", len(pending))
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
