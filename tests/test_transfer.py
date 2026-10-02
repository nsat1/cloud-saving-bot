import asyncio
import hashlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.methods import GetFile
from aiogram.types import File
from yadisk import AsyncClient

from app.media import Attachment
from app.services.file_transfer import FileTooLargeError, FileTransferService, TransferError
from app.services.yandex_disk import StorageError, YandexDiskStorage
from tests.conftest import make_update


@pytest.fixture
def attachment():
    return Attachment.from_message(make_update().message)


async def test_downloaded_bytes_and_name_reach_storage_and_temp_is_removed(
    transfer, storage, bot, attachment
):
    captured = []

    async def upload(source, filename):
        assert source.read_bytes() == b"test"
        assert filename.endswith("_report.pdf")
        captured.append(source)
        return "/saved/" + filename

    storage.upload.side_effect = upload
    path = await transfer.save(attachment, 1, 10)
    assert path.endswith("_report.pdf")
    assert not captured[0].exists()
    bot.download_file.assert_awaited_once()


@pytest.mark.parametrize("kind", ["photo", "document"])
async def test_jpeg_and_exif_reach_yandex_client_byte_for_byte(bot, settings, kind):
    # Искусственный JPEG с EXIF проверяет сохранность изображения вместе с метаданными.
    original = await asyncio.to_thread(
        (Path(__file__).parent / "fixtures" / "photo_with_exif.jpg").read_bytes
    )
    assert original.startswith(b"\xff\xd8")
    assert b"Exif\x00\x00" in original
    message = make_update(kind, file_size=len(original)).message
    if kind == "document":
        message = message.model_copy(
            update={"document": message.document.model_copy(update={"file_name": "IMG_0001.JPG"})}
        )
    attachment = Attachment.from_message(message)
    bot.get_file.return_value = bot.get_file.return_value.model_copy(
        update={"file_size": len(original)}
    )

    async def download(file_path, destination, **kwargs):
        await asyncio.to_thread(Path(destination).write_bytes, original)

    bot.download_file.side_effect = download
    captured = []

    async def upload(source, destination, *, overwrite):
        data = await asyncio.to_thread(Path(source).read_bytes)
        assert data == original
        assert hashlib.sha256(data).digest() == hashlib.sha256(original).digest()
        assert overwrite is True
        assert destination.endswith("_photo.jpg" if kind == "photo" else "_IMG_0001.JPG")
        captured.append(Path(source))

    client = AsyncMock(spec=AsyncClient)
    client.upload.side_effect = upload
    transfer = FileTransferService(
        bot,
        YandexDiskStorage(client, "/photos"),
        max_concurrent_uploads=settings.max_concurrent_uploads,
        max_file_size_mb=settings.max_file_size_mb,
        request_timeout=settings.request_timeout,
    )
    await transfer.save(attachment, 1, 10)
    client.upload.assert_awaited_once()
    assert not captured[0].exists()


async def test_known_oversize_file_is_rejected_before_network(transfer, bot, storage, attachment):
    with pytest.raises(FileTooLargeError, match="20"):
        await transfer.save(replace(attachment, file_size=21 * 1024 * 1024), 1, 10)
    bot.get_file.assert_not_awaited()
    storage.upload.assert_not_awaited()


async def test_get_file_size_is_checked_when_message_size_is_missing(
    transfer, bot, storage, attachment
):
    bot.get_file.return_value = bot.get_file.return_value.model_copy(
        update={"file_size": 21 * 1024 * 1024}
    )
    with pytest.raises(FileTooLargeError):
        await transfer.save(replace(attachment, file_size=None), 1, 10)
    bot.download_file.assert_not_awaited()
    storage.upload.assert_not_awaited()


async def test_actual_download_size_is_checked(transfer, bot, storage, attachment):
    def create_large_file(destination):
        # Разреженный временный файл проверяет лимит без выделения большого буфера.
        with Path(destination).open("wb") as stream:
            stream.truncate(21 * 1024 * 1024)

    async def download(file_path, destination, **kwargs):
        await asyncio.to_thread(create_large_file, destination)

    bot.download_file.side_effect = download
    with pytest.raises(FileTooLargeError):
        await transfer.save(attachment, 1, 10)
    storage.upload.assert_not_awaited()


@pytest.mark.parametrize("stage", ["get_file", "download_file"])
async def test_network_failure_is_retried_and_reported(
    transfer, bot, storage, attachment, monkeypatch, stage
):
    sleep = AsyncMock()
    monkeypatch.setattr("app.services.file_transfer.asyncio.sleep", sleep)
    getattr(bot, stage).side_effect = TimeoutError()
    with pytest.raises(TransferError, match="повторных попыток"):
        await transfer.save(attachment, 1, 10)
    assert getattr(bot, stage).await_count == 3
    assert sleep.await_count == 2
    storage.upload.assert_not_awaited()


async def test_transient_failure_can_recover(transfer, bot, attachment, monkeypatch):
    info = bot.get_file.return_value
    bot.get_file.side_effect = [TimeoutError(), info]
    monkeypatch.setattr("app.services.file_transfer.asyncio.sleep", AsyncMock())
    assert await transfer.save(attachment, 1, 10) == "/bot_uploads/saved"
    assert bot.get_file.await_count == 2


async def test_bad_request_size_is_explained_without_retry(transfer, bot, attachment):
    bot.get_file.side_effect = TelegramBadRequest(
        GetFile(file_id="file-id"), "Bad Request: file is too big"
    )
    with pytest.raises(FileTooLargeError):
        await transfer.save(attachment, 1, 10)
    assert bot.get_file.await_count == 1


async def test_missing_file_path_is_explained(transfer, bot, attachment):
    bot.get_file.return_value = File(file_id="file-id", file_unique_id="unique-id")
    with pytest.raises(TransferError, match="путь"):
        await transfer.save(attachment, 1, 10)
    bot.download_file.assert_not_awaited()


async def test_long_retry_after_does_not_sleep_indefinitely(transfer, bot, attachment):
    bot.get_file.side_effect = TelegramRetryAfter(GetFile(file_id="file-id"), "rate limit", 60)
    with pytest.raises(TransferError, match="ограничил"):
        await transfer.save(attachment, 1, 10)
    assert bot.get_file.await_count == 1


async def test_temp_is_removed_after_storage_failure(transfer, storage, attachment):
    captured = []

    async def upload(source, filename):
        captured.append(source)
        raise StorageError("disk full")

    storage.upload.side_effect = upload
    with pytest.raises(StorageError):
        await transfer.save(attachment, 1, 10)
    assert not captured[0].exists()


async def test_concurrency_limit_and_event_loop_remain_responsive(bot, storage, attachment):
    entered = asyncio.Event()
    release = asyncio.Event()
    active = 0
    maximum = 0

    async def upload(source, filename):
        nonlocal active, maximum
        active += 1
        maximum = max(maximum, active)
        entered.set()
        try:
            await release.wait()
            return filename
        finally:
            active -= 1

    storage.upload.side_effect = upload
    transfer = FileTransferService(
        bot, storage, max_concurrent_uploads=1, max_file_size_mb=20, request_timeout=60
    )
    first = asyncio.create_task(transfer.save(attachment, 1, 10))
    second = asyncio.create_task(transfer.save(attachment, 1, 11))
    try:
        await asyncio.wait_for(entered.wait(), 1)
        # Цикл событий должен оставаться доступным, пока загрузка ожидает завершения.
        await asyncio.wait_for(asyncio.sleep(0), 1)
        assert bot.get_file.await_count == 1
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 1)
        assert maximum == 1
        assert bot.get_file.await_count == 2
    finally:
        release.set()
        for task in (first, second):
            if not task.done():
                task.cancel()
        await asyncio.gather(first, second, return_exceptions=True)


async def test_cancellation_cleans_temp_and_releases_slot(bot, storage, attachment):
    entered = asyncio.Event()
    captured = []

    async def upload(source, filename):
        captured.append(source)
        entered.set()
        await asyncio.Event().wait()

    storage.upload.side_effect = upload
    transfer = FileTransferService(
        bot, storage, max_concurrent_uploads=1, max_file_size_mb=20, request_timeout=60
    )
    task = asyncio.create_task(transfer.save(attachment, 1, 10))
    await asyncio.wait_for(entered.wait(), 1)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not captured[0].exists()
    storage.upload.side_effect = None
    storage.upload.return_value = "/saved"
    assert await asyncio.wait_for(transfer.save(attachment, 1, 11), 1) == "/saved"
