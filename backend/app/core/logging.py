import json
import logging
from contextvars import ContextVar
from importlib import import_module
from typing import Any

from app.core.config import settings

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")
_SENSITIVE_PARTS = ("authorization", "cookie", "database_url", "dsn", "password", "secret", "token")


def sanitize(value: Any, key: str = "") -> Any:
    if any(part in key.casefold() for part in _SENSITIVE_PARTS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(item_key): sanitize(item_value, str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list | tuple):
        return [sanitize(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload["context"] = sanitize(context)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


def configure_sentry() -> bool:
    if not settings.sentry_dsn:
        return False
    try:
        sentry_sdk = import_module("sentry_sdk")
    except ModuleNotFoundError:
        logging.getLogger(__name__).warning("Sentry DSN configurado, mas sentry-sdk não está instalado")
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment,
        send_default_pii=False,
        traces_sample_rate=0.0,
    )
    return True
