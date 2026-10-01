import logging


class RedactTokens(logging.Filter):
    """Скрытие токенов, в том числе в URL запросов внутри исключений SDK."""

    def __init__(self, *tokens: str) -> None:
        super().__init__()
        self._tokens = tuple(token for token in tokens if token)

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if record.exc_info:
            message += "\n" + logging.Formatter().formatException(record.exc_info)
            record.exc_info = None
            record.exc_text = None
        for token in self._tokens:
            message = message.replace(token, "[REDACTED]")
        record.msg = message
        record.args = ()
        return True


def configure_logging(level: str, *tokens: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RedactTokens(*tokens))
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.basicConfig(level=level, handlers=[handler], force=True)
