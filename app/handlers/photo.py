from io import BytesIO
from aiogram import Router, F, Bot
from aiogram.types import ContentType, Message
from app.config import ALLOWED_USERS
from app.services.yandex_disk import upload_photo


router = Router()

@router.message(F.content_type == ContentType.PHOTO)
async def handle_photo(message: Message, bot: Bot):

    if message.from_user.id in ALLOWED_USERS:
        photo = message.photo[-1]
        await message.answer("Загрузка ...")
        file_info = await bot.get_file(photo.file_id)
        byte_stream = BytesIO()
        await bot.download_file(file_info.file_path, destination=byte_stream)
        byte_stream.seek(0)
        result = upload_photo(byte_stream, photo.file_id)

        if result:
            await message.answer("Фото успешно загружено")
        else:
            await message.answer("Ошибка")
    else:
        await message.answer("У Вас нет доступа")
