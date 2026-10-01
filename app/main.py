"""Сборка приложения и управление клиентами. Запуск: python -m app.main."""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from yadisk import AsyncClient

from app.config import ConfigurationError, Settings, load_settings
from app.handlers import create_handlers_router
from app.logging_config import configure_logging
from app.middlewares.access import AccessMiddleware
from app.middlewares.lifecycle import InFlightMiddleware
from app.services.file_transfer import FileTransferService
from app.services.yandex_disk import StorageError, YandexDiskStorage

logger = logging.getLogger(__name__)


def create_dispatcher(
    settings: Settings, file_transfer: FileTransferService, lifecycle: InFlightMiddleware
) -> Dispatcher:
    dispatcher = Dispatcher(disable_fsm=True, file_transfer=file_transfer, settings=settings)
    dispatcher.message.outer_middleware(AccessMiddleware(settings.allowed_ids))
    dispatcher.message.outer_middleware(lifecycle)
    dispatcher.include_router(create_handlers_router())
    return dispatcher


async def run(settings: Settings) -> None:
    session = AiohttpSession(timeout=settings.request_timeout)
    async with (
        Bot(token=settings.bot_token, session=session) as bot,
        AsyncClient(
            token=settings.yandex_token,
            session="aiohttp",
            default_args={
                "timeout": settings.request_timeout,
                "n_retries": 2,
                "retry_interval": 1.0,
            },
        ) as client,
    ):
        storage = YandexDiskStorage(client, settings.yandex_folder)
        await storage.prepare()
        file_transfer = FileTransferService(
            bot,
            storage,
            max_concurrent_uploads=settings.max_concurrent_uploads,
            max_file_size_mb=settings.max_file_size_mb,
            request_timeout=settings.request_timeout,
        )
        lifecycle = InFlightMiddleware()
        dispatcher = create_dispatcher(settings, file_transfer, lifecycle)
        logger.info("Starting bot; destination folder is ready")
        try:
            await bot.delete_webhook(drop_pending_updates=settings.drop_pending_updates)
            await dispatcher.start_polling(
                bot,
                close_bot_session=False,
                tasks_concurrency_limit=settings.max_concurrent_uploads * 4,
                allowed_updates=["message"],
            )
        finally:
            await lifecycle.drain(settings.shutdown_timeout)
            logger.info("Bot stopped")


def main() -> None:
    try:
        settings = load_settings()
    except ConfigurationError as error:
        logging.basicConfig(level=logging.ERROR)
        logger.error("Configuration error: %s", error)
        raise SystemExit(1) from None
    configure_logging(settings.log_level, settings.bot_token, settings.yandex_token)
    try:
        asyncio.run(run(settings))
    except StorageError:
        logger.exception("Could not prepare Yandex Disk")
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        logger.info("Interrupted")
    except Exception:
        logger.exception("Bot stopped due to an unexpected error")
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
