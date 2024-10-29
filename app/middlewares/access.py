from aiogram import BaseMiddleware

from app.config import ALLOWED_USERS


class AccessMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        if user_id not in ALLOWED_USERS:
            await event.answer("У Вас нет доступа")
            return
        return await handler(event, data)
