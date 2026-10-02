from unittest.mock import create_autospec

import pytest
from aiogram.exceptions import TelegramForbiddenError
from aiogram.methods import SendMessage

from app.main import create_dispatcher
from app.middlewares.lifecycle import InFlightMiddleware
from app.services.file_transfer import FileTransferService, TransferError
from app.services.yandex_disk import StorageError
from tests.conftest import make_update


@pytest.fixture
def file_transfer():
    return create_autospec(FileTransferService, instance=True)


@pytest.fixture
def dispatcher(settings, file_transfer):
    return create_dispatcher(settings, file_transfer, InFlightMiddleware())


@pytest.mark.parametrize("kind", ["photo", "video", "document"])
async def test_supported_media_is_saved_before_success(
    dispatcher, file_transfer, bot, answers, kind
):
    async def save(*args):
        assert answers.await_count == 0
        return "/saved"

    file_transfer.save.side_effect = save
    await dispatcher.feed_update(bot, make_update(kind))
    file_transfer.save.assert_awaited_once()
    assert "успешно" in answers.await_args.args[0]


@pytest.mark.parametrize("kind", ["photo", "video", "document", "/start", "text"])
async def test_unauthorized_sender_is_silent(dispatcher, file_transfer, bot, answers, kind):
    await dispatcher.feed_update(bot, make_update(kind, user_id=2))
    file_transfer.save.assert_not_awaited()
    answers.assert_not_awaited()


async def test_message_without_sender_is_ignored(dispatcher, file_transfer, bot, answers):
    await dispatcher.feed_update(bot, make_update(sender=False))
    file_transfer.save.assert_not_awaited()
    answers.assert_not_awaited()


@pytest.mark.parametrize(
    "error",
    [TransferError("download failed"), StorageError("disk full"), OSError("temp unavailable")],
)
async def test_failure_gets_an_answer_without_success(
    dispatcher, file_transfer, bot, answers, error
):
    file_transfer.save.side_effect = error
    await dispatcher.feed_update(bot, make_update())
    answers.assert_awaited_once()
    assert "успешно" not in answers.await_args.args[0]


async def test_acknowledgement_failure_does_not_repeat_upload(
    dispatcher, file_transfer, bot, answers
):
    answers.side_effect = TelegramForbiddenError(
        SendMessage(chat_id=1, text="result"), "bot was blocked"
    )
    await dispatcher.feed_update(bot, make_update())
    file_transfer.save.assert_awaited_once()


async def test_start_describes_actual_features_and_configured_limit(
    dispatcher, file_transfer, bot, answers
):
    await dispatcher.feed_update(bot, make_update("/start"))
    text = answers.await_args.args[0]
    assert all(word in text for word in ("фото", "видео", "документы", "20 МБ"))
    file_transfer.save.assert_not_awaited()


def test_router_can_be_created_for_multiple_dispatchers(settings, file_transfer):
    first = create_dispatcher(settings, file_transfer, InFlightMiddleware())
    second = create_dispatcher(settings, file_transfer, InFlightMiddleware())
    assert first.sub_routers[0] is not second.sub_routers[0]
