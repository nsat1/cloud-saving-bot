"""Ответы на поддерживаемые вложения после завершения передачи файла."""

import logging

from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.media import Attachment
from app.services.file_transfer import FileTransferService, TransferError
from app.services.yandex_disk import StorageError

logger = logging.getLogger(__name__)


async def handle_media(message: Message, file_transfer: FileTransferService) -> None:
    attachment = Attachment.from_message(message)
    try:
        await file_transfer.save(attachment, message.chat.id, message.message_id)
    except (TransferError, StorageError) as error:
        logger.warning(
            "Media transfer failed chat_id=%s message_id=%s",
            message.chat.id,
            message.message_id,
            exc_info=True,
        )
        response = str(error)
    except OSError:
        logger.exception(
            "Temporary file failure chat_id=%s message_id=%s",
            message.chat.id,
            message.message_id,
        )
        response = "Не удалось обработать файл. Обратитесь к владельцу бота."
    except Exception:
        logger.exception(
            "Unexpected transfer failure chat_id=%s message_id=%s",
            message.chat.id,
            message.message_id,
        )
        response = "Не удалось сохранить файл. Попробуйте позже."
    else:
        verb = "сохранён" if attachment.label == "Документ" else "сохранено"
        response = f"{attachment.label} успешно {verb} на Яндекс.Диск 🙌"
    try:
        await message.answer(response)
    except TelegramAPIError:
        # Ошибка отправки подтверждения не должна приводить к повторной загрузке файла.
        logger.warning(
            "Could not send transfer result chat_id=%s message_id=%s",
            message.chat.id,
            message.message_id,
            exc_info=True,
        )
