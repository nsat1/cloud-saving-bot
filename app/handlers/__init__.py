from aiogram import Router


def get_handlers_router() -> Router:
    from . import start, photo, document

    router = Router()
    router.include_router(start.router)
    router.include_router(photo.router)
    router.include_router(document.router)

    return router
