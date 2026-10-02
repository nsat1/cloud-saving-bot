import pytest

from app.config import ConfigurationError, Settings


def environment(**overrides):
    return {
        "BOT_TOKEN": "123456:TEST_TOKEN",
        "YANDEX_TOKEN": "test-yandex-token",
        "ALLOWED_IDS": "1, 2,1",
        **overrides,
    }


def test_defaults_and_secret_repr():
    settings = Settings.from_env(environment())
    assert settings.allowed_ids == frozenset({1, 2})
    assert settings.yandex_folder == "/bot_uploads"
    assert settings.drop_pending_updates is False
    assert "TEST_TOKEN" not in repr(settings)
    assert "test-yandex-token" not in repr(settings)


@pytest.mark.parametrize("variable", ["BOT_TOKEN", "YANDEX_TOKEN", "ALLOWED_IDS"])
def test_required_settings_name_missing_variable(variable):
    env = environment()
    env.pop(variable)
    with pytest.raises(ConfigurationError, match=variable):
        Settings.from_env(env)


@pytest.mark.parametrize("value", ["", " ", "1,", ",1", "1,,2", "abc", "0", "-1"])
def test_invalid_allowlist_fails_closed(value):
    with pytest.raises(ConfigurationError, match="ALLOWED_IDS"):
        Settings.from_env(environment(ALLOWED_IDS=value))


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        ("BOT_TOKEN", "not-a-token"),
        ("YANDEX_FOLDER", "/"),
        ("YANDEX_FOLDER", "/one/../two"),
        ("YANDEX_FOLDER", "/one//two"),
        ("YANDEX_FOLDER", "disk:/folder"),
        ("YANDEX_FOLDER", "one\\two"),
        ("MAX_FILE_SIZE_MB", "21"),
        ("MAX_CONCURRENT_UPLOADS", "0"),
        ("REQUEST_TIMEOUT", "x"),
        ("SHUTDOWN_TIMEOUT", "-1"),
        ("DROP_PENDING_UPDATES", "yes"),
        ("LOG_LEVEL", "unknown"),
    ],
)
def test_invalid_options(variable, value):
    with pytest.raises(ConfigurationError, match=variable):
        Settings.from_env(environment(**{variable: value}))


def test_custom_folder_and_options():
    settings = Settings.from_env(
        environment(
            YANDEX_FOLDER=" /archive/photos/ ", DROP_PENDING_UPDATES="TRUE", LOG_LEVEL="debug"
        )
    )
    assert settings.yandex_folder == "/archive/photos"
    assert settings.drop_pending_updates is True
    assert settings.log_level == "DEBUG"
