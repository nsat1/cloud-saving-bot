import io
import logging

from app.logging_config import RedactTokens


def test_tokens_are_redacted_in_message_and_traceback():
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.addFilter(RedactTokens("bot-secret", "disk-secret"))
    logger = logging.Logger("redaction-test")
    logger.addHandler(handler)
    try:
        raise RuntimeError("https://api.telegram.org/file/botbot-secret/path disk-secret")
    except RuntimeError:
        logger.exception("Request failed: %s", "bot-secret")
    result = output.getvalue()
    assert "bot-secret" not in result
    assert "disk-secret" not in result
    assert "[REDACTED]" in result
    assert "RuntimeError" in result
