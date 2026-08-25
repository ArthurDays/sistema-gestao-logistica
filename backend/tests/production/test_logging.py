import json
import logging

from app.core.logging import JsonFormatter, request_id_context, sanitize


def test_sensitive_context_is_redacted_recursively() -> None:
    result = sanitize(
        {"email": "user@example.com", "authorization": "Bearer value", "nested": {"password": "x"}}
    )
    assert result == {
        "email": "user@example.com",
        "authorization": "[REDACTED]",
        "nested": {"password": "[REDACTED]"},
    }


def test_json_formatter_includes_request_id_without_secret() -> None:
    token = request_id_context.set("request-123")
    try:
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "processed", (), None)
        record.context = {"token": "private", "status_code": 200}  # type: ignore[attr-defined]
        payload = json.loads(JsonFormatter().format(record))
    finally:
        request_id_context.reset(token)

    assert payload["request_id"] == "request-123"
    assert payload["context"] == {"token": "[REDACTED]", "status_code": 200}
