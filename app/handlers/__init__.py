from aiogram import F, Router
from aiogram.filters import CommandStart

from app.handlers.media import handle_media
from app.handlers.other import handle_other_messages
from app.handlers.start import start_command


def create_handlers_router() -> Router:
    router = Router(name="messages")
    router.message.register(start_command, CommandStart())
    router.message.register(handle_media, F.photo | F.video | F.document)
    router.message.register(handle_other_messages)
    return router
