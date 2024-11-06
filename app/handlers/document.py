from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.types import ContentType, Message

from app.services.yandex_disk import upload_photo

router = Router(name="document")

@router.message(F.content_type == ContentType.DOCUMENT)
async def handle_document(message: Message, bot: Bot):
    """
    Обрабатывает сообщения с документами, загружает их на Яндекс Диск.

    :param message: Объект сообщения, содержащий документ.
    :type message: Message
    :param bot: Объект бота для взаимодействия с Telegram API.
    :type bot: Bot
    """

    document = message.document
    file_info = await bot.get_file(document.file_id)

    with BytesIO() as byte_stream:
        await bot.download_file(file_info.file_path, destination=byte_stream)
        byte_stream.seek(0)
        result = upload_photo(byte_stream, document.file_id)

        if result:
            await message.answer("Документ успешно загружен 🙌")
        else:
            await message.answer("Ошибка при загрузке")
