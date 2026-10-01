"""Скачивание вложений Telegram во временный файл и передача в хранилище."""

import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from aiogram import Bot
from aiogram.exceptions import (
    TelegramAPIError,
    TelegramBadRequest,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiohttp import ClientError

from app.media import Attachment
from app.services.yandex_disk import YandexDiskStorage

logger = logging.getLogger(__name__)
MIB = 1024 * 1024


class TransferError(Exception):
    """Ошибка скачивания с безопасным пояснением для пользователя."""


class FileTooLargeError(TransferError):
    def __init__(self, maximum_mb: int) -> None:
        super().__init__(
            f"Файл слишком большой. Максимальный размер для сохранения — {maximum_mb} МБ."
        )


class FileTransferService:
    def __init__(
        self,
        bot: Bot,
        storage: YandexDiskStorage,
        *,
        max_concurrent_uploads: int,
        max_file_size_mb: int,
        request_timeout: int,
    ) -> None:
        self._bot = bot
        self._storage = storage
        self._semaphore = asyncio.Semaphore(max_concurrent_uploads)
        self._max_file_size_mb = max_file_size_mb
        self._max_bytes = max_file_size_mb * MIB
        self._request_timeout = request_timeout

    def _check_size(self, size: int | None) -> None:
        if size is not None and size > self._max_bytes:
            raise FileTooLargeError(self._max_file_size_mb)

    async def save(self, attachment: Attachment, chat_id: int, message_id: int) -> str:
        self._check_size(attachment.file_size)
        async with self._semaphore:
            with TemporaryDirectory(prefix="cloud-saving-bot-") as directory:
                source = Path(directory) / "download"
                await self._download(attachment, source)
                self._check_size(source.stat().st_size)
                destination = await self._storage.upload(
                    source, attachment.destination_name(chat_id, message_id)
                )
        logger.info("Saved media chat_id=%s message_id=%s", chat_id, message_id)
        return destination

    async def _download(self, attachment: Attachment, destination: Path) -> None:
        for attempt in range(3):
            delay = float(2**attempt)
            try:
                info = await self._bot.get_file(attachment.file_id)
                self._check_size(info.file_size)
                if not info.file_path:
                    raise TransferError("Telegram не предоставил путь к файлу.")
                await self._bot.download_file(
                    info.file_path,
                    destination=destination,
                    timeout=self._request_timeout,
                )
                return
            except TelegramBadRequest as error:
                if "file is too big" in error.message.lower():
                    raise FileTooLargeError(self._max_file_size_mb) from error
                raise TransferError("Telegram не смог предоставить файл для скачивания.") from error
            except TelegramRetryAfter as error:
                if error.retry_after > 5:
                    raise TransferError(
                        "Telegram временно ограничил запросы. Попробуйте позже."
                    ) from error
                delay = float(error.retry_after)
            except (TelegramNetworkError, TelegramServerError, ClientError, TimeoutError):
                pass
            except TelegramAPIError as error:
                raise TransferError(
                    "Не удалось скачать файл из Telegram. Попробуйте позже."
                ) from error
            if attempt < 2:
                logger.warning("Retrying Telegram download, attempt=%s", attempt + 2)
                await asyncio.sleep(delay)
        raise TransferError("Не удалось скачать файл из Telegram после повторных попыток.")
