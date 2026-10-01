from aiogram.types import Message


async def handle_other_messages(message: Message) -> None:
    await message.answer(
        "Отправь или перешли фото, видео или документ — я сохраню его на Яндекс.Диск."
    )
