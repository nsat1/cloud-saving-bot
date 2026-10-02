import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, create_autospec

import pytest
from aiogram import Bot
from aiogram.types import File, Message, Update

from app.config import Settings
from app.services.file_transfer import FileTransferService
from app.services.yandex_disk import YandexDiskStorage

TEST_TOKEN = "123456:TEST_TOKEN_FOR_UNIT_TESTS"


@pytest.fixture
def settings() -> Settings:
    return Settings.from_env(
        {"BOT_TOKEN": TEST_TOKEN, "YANDEX_TOKEN": "test-yandex-token", "ALLOWED_IDS": "1"}
    )


@pytest.fixture
async def bot(monkeypatch):
    instance = Bot(TEST_TOKEN)
    monkeypatch.setattr(
        instance,
        "get_file",
        AsyncMock(
            return_value=File(
                file_id="file-id",
                file_unique_id="unique-id",
                file_path="documents/file",
                file_size=4,
            )
        ),
    )

    async def download(file_path, destination, **kwargs):
        await asyncio.to_thread(Path(destination).write_bytes, b"test")

    monkeypatch.setattr(instance, "download_file", AsyncMock(side_effect=download))
    yield instance
    await instance.session.close()


@pytest.fixture
def storage():
    instance = create_autospec(YandexDiskStorage, instance=True)
    instance.upload.return_value = "/bot_uploads/saved"
    return instance


@pytest.fixture
def transfer(bot, storage, settings):
    return FileTransferService(
        bot,
        storage,
        max_concurrent_uploads=settings.max_concurrent_uploads,
        max_file_size_mb=settings.max_file_size_mb,
        request_timeout=settings.request_timeout,
    )


@pytest.fixture
def answers(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr(Message, "answer", mock)
    return mock


def make_update(kind="document", user_id=1, message_id=10, *, sender=True, file_size=4):
    message = {
        "message_id": message_id,
        "date": 1,
        "chat": {"id": user_id, "type": "private"},
    }
    if sender:
        message["from"] = {"id": user_id, "is_bot": False, "first_name": "Test"}
    media = {"file_id": "file-id", "file_unique_id": "unique-id", "file_size": file_size}
    if kind == "photo":
        message["photo"] = [
            dict(media, width=10, height=10),
            dict(media, file_id="large-photo-id", width=100, height=100),
        ]
    elif kind == "video":
        message["video"] = dict(
            media, width=10, height=10, duration=1, file_name="clip.mp4", mime_type="video/mp4"
        )
    elif kind == "document":
        message["document"] = dict(media, file_name="report.pdf", mime_type="application/pdf")
    else:
        message["text"] = kind
    return Update.model_validate({"update_id": message_id, "message": message})
