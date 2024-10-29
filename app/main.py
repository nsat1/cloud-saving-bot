import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.middlewares.access import AccessMiddleware
from app.handlers import get_handlers_router


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(AccessMiddleware())
dp.include_router(get_handlers_router())

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
