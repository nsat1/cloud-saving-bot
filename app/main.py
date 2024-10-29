import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from app.handlers import start, photo
from app.filters.access import AccessMiddleware


logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(AccessMiddleware())
dp.include_router(start.router)
dp.include_router(photo.router)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
