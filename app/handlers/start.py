from aiogram import Router, types
from aiogram.filters import Command

router = Router(name="start")

@router.message(Command(commands=["start"]))
async def start_command(message: types.Message):
    user_name = message.from_user.full_name
    await message.answer(f"Привет, {user_name}🖐️\n"
                         f"\nЯ умею сохранять фото📷 на Яндекс Диск.\n"
                         f"\nОтправь мне фото📷, которые нужно сохранить или перешли их в чат.")
