"""Загрузка и проверка настроек при запуске приложения."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from aiogram.utils.token import TokenValidationError, validate_token
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class ConfigurationError(ValueError):
    """Переменная окружения отсутствует или содержит недопустимое значение."""


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise ConfigurationError(f"{name}: обязательное значение не задано")
    return value


def _integer(env: Mapping[str, str], name: str, default: int, maximum: int) -> int:
    try:
        value = int(env.get(name, str(default)))
    except ValueError:
        raise ConfigurationError(f"{name}: требуется целое число") from None
    if not 1 <= value <= maximum:
        raise ConfigurationError(f"{name}: допустимый диапазон — 1..{maximum}")
    return value


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str = field(repr=False)
    yandex_token: str = field(repr=False)
    allowed_ids: frozenset[int]
    yandex_folder: str = "/bot_uploads"
    max_concurrent_uploads: int = 2
    max_file_size_mb: int = 20
    request_timeout: int = 60
    shutdown_timeout: int = 30
    drop_pending_updates: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        bot_token = _required(env, "BOT_TOKEN")
        try:
            validate_token(bot_token)
        except TokenValidationError:
            raise ConfigurationError("BOT_TOKEN: неверный формат токена Telegram") from None
        yandex_token = _required(env, "YANDEX_TOKEN")
        raw_ids = _required(env, "ALLOWED_IDS")
        try:
            allowed_ids = frozenset(int(item.strip()) for item in raw_ids.split(","))
        except ValueError:
            raise ConfigurationError(
                "ALLOWED_IDS: укажите положительные ID через запятую, без пустых элементов"
            ) from None
        if any(user_id <= 0 for user_id in allowed_ids):
            raise ConfigurationError("ALLOWED_IDS: все ID должны быть положительными")

        folder = env.get("YANDEX_FOLDER", "/bot_uploads").strip().strip("/")
        if not folder or any(part in {"", ".", ".."} for part in folder.split("/")):
            raise ConfigurationError("YANDEX_FOLDER: укажите путь к папке без . и ..")
        if "\\" in folder or ":" in folder or any(ord(char) < 32 for char in folder):
            raise ConfigurationError("YANDEX_FOLDER: недопустимые символы в пути")

        raw_drop = env.get("DROP_PENDING_UPDATES", "false").strip().lower()
        if raw_drop not in {"true", "false"}:
            raise ConfigurationError("DROP_PENDING_UPDATES: используйте true или false")
        log_level = env.get("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ConfigurationError("LOG_LEVEL: неизвестный уровень логирования")
        return cls(
            bot_token=bot_token,
            yandex_token=yandex_token,
            allowed_ids=allowed_ids,
            yandex_folder="/" + folder,
            max_concurrent_uploads=_integer(env, "MAX_CONCURRENT_UPLOADS", 2, 16),
            max_file_size_mb=_integer(env, "MAX_FILE_SIZE_MB", 20, 20),
            request_timeout=_integer(env, "REQUEST_TIMEOUT", 60, 600),
            shutdown_timeout=_integer(env, "SHUTDOWN_TIMEOUT", 30, 600),
            drop_pending_updates=raw_drop == "true",
            log_level=log_level,
        )


def load_settings() -> Settings:
    load_dotenv(ENV_FILE, override=False)
    return Settings.from_env(os.environ)
