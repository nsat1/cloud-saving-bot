import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock, Mock, create_autospec

import pytest
from yadisk import AsyncClient

from app.config import ConfigurationError
from app.main import main, run
from app.services.yandex_disk import StorageError
from tests.conftest import make_update


@pytest.fixture
def runtime_clients(bot, monkeypatch):
    client = create_autospec(AsyncClient, instance=True)
    client.__aenter__.return_value = client
    client.check_token.return_value = True
    client_factory = Mock(return_value=client)
    monkeypatch.setattr("app.main.AsyncClient", client_factory)
    monkeypatch.setattr("app.main.Bot", Mock(return_value=bot))
    monkeypatch.setattr(bot, "delete_webhook", AsyncMock())
    monkeypatch.setattr(bot.session, "close", AsyncMock())
    return client, client_factory


@pytest.mark.parametrize("drop_pending", [False, True])
async def test_runtime_prepares_storage_before_polling_and_closes_clients(
    settings, bot, runtime_clients, monkeypatch, drop_pending
):
    client, factory = runtime_clients
    options = {}

    async def polling(dispatcher, *bots, **kwargs):
        client.check_token.assert_awaited_once()
        client.mkdir.assert_awaited_once_with("/bot_uploads")
        options.update(kwargs)

    monkeypatch.setattr("app.main.Dispatcher.start_polling", polling)
    await run(replace(settings, drop_pending_updates=drop_pending))
    bot.delete_webhook.assert_awaited_once_with(drop_pending_updates=drop_pending)
    assert options["close_bot_session"] is False
    assert options["tasks_concurrency_limit"] == 8
    assert options["allowed_updates"] == ["message"]
    assert factory.call_args.kwargs["session"] == "aiohttp"
    assert factory.call_args.kwargs["default_args"]["n_retries"] == 2
    client.__aexit__.assert_awaited_once()
    bot.session.close.assert_awaited_once()


async def test_startup_storage_failure_closes_clients_without_polling(
    settings, bot, runtime_clients, monkeypatch
):
    client, _ = runtime_clients
    client.check_token.return_value = False
    polling = AsyncMock()
    monkeypatch.setattr("app.main.Dispatcher.start_polling", polling)
    with pytest.raises(StorageError):
        await run(settings)
    polling.assert_not_awaited()
    bot.delete_webhook.assert_not_awaited()
    client.__aexit__.assert_awaited_once()
    bot.session.close.assert_awaited_once()


async def test_shutdown_finishes_upload_and_response_before_closing_sessions(
    settings, bot, runtime_clients, monkeypatch, answers
):
    client, _ = runtime_clients
    entered = asyncio.Event()
    release = asyncio.Event()
    timeline = []
    tasks = []

    async def upload(source, destination, **kwargs):
        entered.set()
        await release.wait()
        timeline.append("uploaded")

    async def exit_client(*args):
        assert answers.await_count == 1
        timeline.append("closed")

    async def polling(dispatcher, *bots, **kwargs):
        tasks.append(asyncio.create_task(dispatcher.feed_update(bot, make_update())))
        await asyncio.wait_for(entered.wait(), 1)
        asyncio.get_running_loop().call_later(0.01, release.set)

    client.upload.side_effect = upload
    client.__aexit__.side_effect = exit_client
    monkeypatch.setattr("app.main.Dispatcher.start_polling", polling)
    try:
        await run(settings)
        assert timeline == ["uploaded", "closed"]
        assert tasks[0].done()
        assert "успешно" in answers.await_args.args[0]
    finally:
        release.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


def test_configuration_failure_exits_before_creating_runtime(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.main.load_settings", Mock(side_effect=ConfigurationError("ALLOWED_IDS: missing"))
    )
    runner = Mock()
    monkeypatch.setattr("app.main.run", runner)
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert "ALLOWED_IDS" in caplog.text
    runner.assert_not_called()
