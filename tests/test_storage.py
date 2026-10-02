from pathlib import Path
from unittest.mock import create_autospec

import pytest
from yadisk import AsyncClient
from yadisk.exceptions import (
    ForbiddenError,
    InsufficientStorageError,
    ParentNotFoundError,
    PathExistsError,
    RequestError,
    UnauthorizedError,
)

from app.services.yandex_disk import StorageError, YandexDiskStorage


@pytest.fixture
def client():
    mock = create_autospec(AsyncClient, instance=True)
    mock.check_token.return_value = True
    return mock


async def test_prepare_creates_nested_folder_and_checks_existing_parents(client):
    client.mkdir.side_effect = [PathExistsError(), None]
    client.is_dir.return_value = True
    await YandexDiskStorage(client, "/archive/files").prepare()
    assert [call.args[0] for call in client.mkdir.await_args_list] == ["/archive", "/archive/files"]
    client.is_dir.assert_awaited_once_with("/archive")


async def test_prepare_rejects_existing_file(client):
    client.mkdir.side_effect = PathExistsError()
    client.is_dir.return_value = False
    with pytest.raises(StorageError, match="занят файлом"):
        await YandexDiskStorage(client, "/archive").prepare()


async def test_invalid_token_prevents_folder_creation(client):
    client.check_token.return_value = False
    with pytest.raises(StorageError, match="YANDEX_TOKEN"):
        await YandexDiskStorage(client, "/archive").prepare()
    client.mkdir.assert_not_awaited()


async def test_upload_uses_async_client_and_idempotent_path(client, tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"file")
    result = await YandexDiskStorage(client, "/archive").upload(source, "1_10_report.pdf")
    assert result == "/archive/1_10_report.pdf"
    client.upload.assert_awaited_once_with(str(source), result, overwrite=True)


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (UnauthorizedError(), "Нет доступа"),
        (ForbiddenError(), "Нет доступа"),
        (InsufficientStorageError(), "свободное место"),
        (ParentNotFoundError(), "Папка"),
        (RequestError(), "Попробуйте позже"),
    ],
)
async def test_upload_maps_sdk_errors(client, error, message):
    client.upload.side_effect = error
    with pytest.raises(StorageError, match=message):
        await YandexDiskStorage(client, "/archive").upload(Path("source"), "file.pdf")
