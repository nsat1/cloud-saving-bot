from aiogram import Router, types
from aiogram.filters import Command

router = Router()

@router.message(Command(commands=["start"]))
async def start_command(message: types.Message):
    user_name = message.from_user.full_name
    await message.answer(f"Hello, {user_name}!")
