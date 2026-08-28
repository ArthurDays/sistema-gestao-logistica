import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import PasswordResetToken, User
from app.password_reset import (
    PasswordResetRejected,
    confirm_password_reset,
    request_password_reset,
)


class RecordingSender:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, reset_url: str) -> None:
        self.messages.append((recipient, reset_url))


def _raw_token(reset_url: str) -> str:
    return reset_url.split("reset_token=", 1)[1]


def test_request_persists_only_hash_invalidates_previous_and_limits_rate(
    db_session: Session,
) -> None:
    sender = RecordingSender()
    for _attempt in range(4):
        request_password_reset(
            " ADMIN@TESTE.LOCAL ",
            "test-origin",
            "https://logisync.example.test/",
            sender,
            db_session,
        )

    tokens = list(db_session.scalars(select(PasswordResetToken)))
    pending = [token for token in tokens if token.used_at is None]
    assert len(sender.messages) == 3
    assert len(tokens) == 3
    assert len(pending) == 1
    for (_recipient, reset_url), token in zip(sender.messages, tokens, strict=True):
        raw_token = _raw_token(reset_url)
        assert token.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
        assert raw_token not in token.token_hash


def test_confirm_changes_password_once_and_rejects_expired_or_current_password(
    db_session: Session,
) -> None:
    sender = RecordingSender()
    now = datetime.now(UTC)
    request_password_reset(
        "admin@teste.local",
        "test-origin",
        "https://logisync.example.test/",
        sender,
        db_session,
        now=now,
    )
    raw_token = _raw_token(sender.messages[-1][1])

    with pytest.raises(PasswordResetRejected):
        confirm_password_reset(raw_token, "senha-de-teste-segura", db_session, now=now)

    confirm_password_reset(raw_token, "nova-senha-segura-123", db_session, now=now)
    user = db_session.scalar(select(User).where(User.email == "admin@teste.local"))
    assert user is not None
    assert verify_password("nova-senha-segura-123", user.password_hash)
    with pytest.raises(PasswordResetRejected):
        confirm_password_reset(raw_token, "outra-senha-segura-123", db_session, now=now)

    request_password_reset(
        "admin@teste.local",
        "another-origin",
        "https://logisync.example.test/",
        sender,
        db_session,
        now=now,
    )
    expired_token = _raw_token(sender.messages[-1][1])
    with pytest.raises(PasswordResetRejected):
        confirm_password_reset(
            expired_token,
            "outra-senha-segura-123",
            db_session,
            now=now + timedelta(minutes=31),
        )
