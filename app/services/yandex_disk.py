"""Асинхронный адаптер для Яндекс Диска."""

from pathlib import Path

from yadisk import AsyncClient
from yadisk.exceptions import (
    ForbiddenError,
    InsufficientStorageError,
    ParentNotFoundError,
    PathExistsError,
    PathNotFoundError,
    UnauthorizedError,
    WrongResourceTypeError,
    YaDiskError,
)


class StorageError(Exception):
    """Ошибка хранилища с безопасным пояснением для пользователя."""


def _storage_error(error: YaDiskError) -> StorageError:
    if isinstance(error, (UnauthorizedError, ForbiddenError)):
        return StorageError("Нет доступа к Яндекс.Диску. Обратитесь к владельцу бота.")
    if isinstance(error, InsufficientStorageError):
        return StorageError("На Яндекс.Диске закончилось свободное место.")
    if isinstance(error, (ParentNotFoundError, PathNotFoundError, WrongResourceTypeError)):
        return StorageError("Папка сохранения недоступна. Обратитесь к владельцу бота.")
    return StorageError("Не удалось загрузить файл на Яндекс.Диск. Попробуйте позже.")


class YandexDiskStorage:
    def __init__(self, client: AsyncClient, folder: str) -> None:
        self._client = client
        self._folder = folder

    async def prepare(self) -> None:
        """Проверить токен и создать недостающие родительские папки."""
        try:
            if not await self._client.check_token():
                raise StorageError("YANDEX_TOKEN: токен недействителен")
            path = ""
            for part in self._folder.strip("/").split("/"):
                path += "/" + part
                try:
                    await self._client.mkdir(path)
                except PathExistsError:
                    if not await self._client.is_dir(path):
                        raise StorageError(
                            "YANDEX_FOLDER: путь занят файлом, укажите другую папку"
                        ) from None
        except YaDiskError as error:
            raise _storage_error(error) from error

    async def upload(self, source: Path, filename: str) -> str:
        destination = self._folder + "/" + filename
        try:
            await self._client.upload(str(source), destination, overwrite=True)
        except YaDiskError as error:
            raise _storage_error(error) from error
        return destination
