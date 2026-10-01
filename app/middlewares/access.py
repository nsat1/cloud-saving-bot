"""Игнорирование сообщений от пользователей вне списка доступа без ответа."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject


class AccessMiddleware(BaseMiddleware):
    def __init__(self, allowed_ids: frozenset[int]) -> None:
        self._allowed_ids = allowed_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return None
        if event.from_user is None or event.from_user.id not in self._allowed_ids:
            return None
        return await handler(event, data)
