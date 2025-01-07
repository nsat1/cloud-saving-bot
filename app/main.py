import logging
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import BOT_TOKEN
from middlewares.access import AccessMiddleware
from handlers import get_handlers_router


logging.basicConfig(
    level=logging.INFO,
    format='%(filename)s:%(lineno)d #%(levelname)-8s '
           '[%(asctime)s] - %(name)s - %(message)s')


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

dp.message.middleware(AccessMiddleware())
dp.include_router(get_handlers_router())

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
