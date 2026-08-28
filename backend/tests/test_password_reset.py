import hashlib
import re
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from time import perf_counter

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import AuthLoginThrottle

NEUTRAL_MESSAGE = "Se a conta puder ser recuperada, enviaremos as instruções."


class FakeSmtp:
    sent_messages: list[EmailMessage] = []

    def __init__(self, host: str, port: int, *, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> "FakeSmtp":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, _username: str, _password: str) -> None:
        return None

    def send_message(self, message: EmailMessage) -> None:
        self.sent_messages.append(message)


def _configure_smtp(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeSmtp.sent_messages.clear()
    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    monkeypatch.setattr(settings, "smtp_host", "smtp.example.test")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_username", "mailer")
    monkeypatch.setattr(settings, "smtp_password", "secret")
    monkeypatch.setattr(settings, "smtp_from_email", "no-reply@example.test")
    monkeypatch.setattr(settings, "smtp_timeout_seconds", 1.0)
    monkeypatch.setattr(settings, "smtp_starttls", True)
    monkeypatch.setattr(settings, "frontend_url", "https://logisync.example.test")


def _token_from_message(message: EmailMessage) -> str:
    match = re.search(r"https://[^\s]+\?reset_token=([A-Za-z0-9_-]+)", message.get_content())
    assert match is not None
    return match.group(1)


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-001
def test_ac001_requests_password_reset_without_exposing_account(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_smtp(monkeypatch)

    started_at = perf_counter()
    response = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": " ADMIN@TESTE.LOCAL "},
    )
    elapsed = perf_counter() - started_at

    assert response.status_code == 202
    assert response.json() == {"message": NEUTRAL_MESSAGE}
    assert elapsed < 2
    assert len(FakeSmtp.sent_messages) == 1
    body = FakeSmtp.sent_messages[0].get_content()
    links = re.findall(r"https://[^\s]+\?reset_token=[A-Za-z0-9_-]+", body)
    assert len(links) == 1
    assert "admin@teste.local" not in response.text.casefold()


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-002
def test_ac002_unknown_account_and_rate_limit_are_neutral(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_smtp(monkeypatch)
    unknown = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "unknown@example.test"},
    )

    assert unknown.status_code == 202
    assert unknown.json() == {"message": NEUTRAL_MESSAGE}
    assert FakeSmtp.sent_messages == []
    assert db_session.scalar(text("SELECT COUNT(*) FROM password_reset_tokens")) == 0

    db_session.execute(delete(AuthLoginThrottle))
    db_session.commit()
    responses = [
        client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "admin@teste.local"},
        )
        for _attempt in range(4)
    ]

    assert all(response.status_code == 202 for response in responses)
    assert all(response.json() == {"message": NEUTRAL_MESSAGE} for response in responses)
    assert len(FakeSmtp.sent_messages) == 3
    assert db_session.scalar(
        text("SELECT COUNT(*) FROM password_reset_tokens WHERE used_at IS NULL")
    ) == 1


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-003
def test_ac003_consumes_token_once_and_allows_new_login(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_smtp(monkeypatch)
    for _request in range(2):
        response = client.post(
            "/api/v1/auth/password-reset/request",
            json={"email": "admin@teste.local"},
        )
        assert response.status_code == 202
    old_token = _token_from_message(FakeSmtp.sent_messages[0])
    current_token = _token_from_message(FakeSmtp.sent_messages[1])
    payload = {
        "token": current_token,
        "password": "nova-senha-segura-123",
        "password_confirmation": "nova-senha-segura-123",
    }

    confirmed = client.post("/api/v1/auth/password-reset/confirm", json=payload)

    assert confirmed.status_code == 204
    assert client.post("/api/v1/auth/password-reset/confirm", json=payload).status_code == 400
    assert client.post(
        "/api/v1/auth/password-reset/confirm",
        json={**payload, "token": old_token},
    ).status_code == 400
    assert client.post(
        "/api/v1/auth/token",
        json={"email": "admin@teste.local", "password": "senha-de-teste-segura"},
    ).status_code == 401
    assert client.post(
        "/api/v1/auth/token",
        json={"email": "admin@teste.local", "password": "nova-senha-segura-123"},
    ).status_code == 200


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-004
def test_ac004_rejects_expired_reused_or_invalid_password(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_smtp(monkeypatch)
    requested = client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "admin@teste.local"},
    )
    assert requested.status_code == 202
    token = _token_from_message(FakeSmtp.sent_messages[-1])
    invalid_passwords = [
        ({"password": "curta", "password_confirmation": "curta"}, 422),
        (
            {
                "password": "senha-nova-segura-123",
                "password_confirmation": "senha-diferente-123",
            },
            422,
        ),
        (
            {
                "password": "senha-de-teste-segura",
                "password_confirmation": "senha-de-teste-segura",
            },
            400,
        ),
    ]
    for passwords, expected_status in invalid_passwords:
        response = client.post(
            "/api/v1/auth/password-reset/confirm",
            json={"token": token, **passwords},
        )
        assert response.status_code == expected_status

    valid_payload = {
        "token": token,
        "password": "senha-final-segura-123",
        "password_confirmation": "senha-final-segura-123",
    }
    assert client.post("/api/v1/auth/password-reset/confirm", json=valid_payload).status_code == 204
    assert client.post("/api/v1/auth/password-reset/confirm", json=valid_payload).status_code == 400

    assert client.post(
        "/api/v1/auth/password-reset/request",
        json={"email": "admin@teste.local"},
    ).status_code == 202
    expired_token = _token_from_message(FakeSmtp.sent_messages[-1])
    db_session.execute(
        text(
            "UPDATE password_reset_tokens SET expires_at = :expired "
            "WHERE token_hash = :token_hash"
        ),
        {
            "expired": datetime.now(UTC) - timedelta(seconds=1),
            "token_hash": hashlib.sha256(expired_token.encode()).hexdigest(),
        },
    )
    db_session.commit()

    expired = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={**valid_payload, "token": expired_token, "password": "outra-senha-segura-123",
              "password_confirmation": "outra-senha-segura-123"},
    )
    unknown = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={**valid_payload, "token": "token-desconhecido-com-entropia-suficiente"},
    )
    assert expired.status_code == 400
    assert unknown.status_code == 400
    assert expired.json() == unknown.json()
