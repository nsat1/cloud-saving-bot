from aiogram.types import Message

from app.config import Settings


async def start_command(message: Message, settings: Settings) -> None:
    name = message.from_user.full_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {name}!\n\n"
        "Я сохраняю фото, видео и документы на Яндекс.Диск. "
        f"Максимальный размер файла — {settings.max_file_size_mb} МБ. "
        "Отправь или перешли мне файл. "
        "Фото сохраняются в наибольшем размере, доступном в сообщении. "
        "Чтобы сохранить оригинал без сжатия Telegram, отправь его как документ."
    )
