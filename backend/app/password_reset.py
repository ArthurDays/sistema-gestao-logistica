import hashlib
import hmac
import logging
import secrets
import smtplib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models import AuthLoginThrottle, PasswordResetToken, User

logger = logging.getLogger(__name__)

RESET_TOKEN_TTL = timedelta(minutes=30)
RESET_THROTTLE_WINDOW = timedelta(hours=1)
RESET_THROTTLE_LIMIT = 3
_IDENTITY_SCOPE = "reset_identity"
_ORIGIN_SCOPE = "reset_origin"


class PasswordResetRejected(Exception):
    """A confirmação não pode prosseguir sem revelar o motivo sensível."""


class PasswordResetSender(Protocol):
    def send(self, recipient: str, reset_url: str) -> None: ...


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    from_email: str
    username: str | None = None
    password: str | None = None
    timeout_seconds: float = 5.0
    starttls: bool = True


class SmtpPasswordResetSender:
    def __init__(self, config: SmtpConfig) -> None:
        self.config = config

    def send(self, recipient: str, reset_url: str) -> None:
        message = EmailMessage()
        message["Subject"] = "Redefinição de senha do LogiSync"
        message["From"] = self.config.from_email
        message["To"] = recipient
        message.set_content(
            "Recebemos uma solicitação para redefinir sua senha.\n\n"
            f"Use este link único, válido por 30 minutos:\n{reset_url}\n\n"
            "Se você não fez a solicitação, ignore esta mensagem."
        )
        with smtplib.SMTP(
            self.config.host,
            self.config.port,
            timeout=self.config.timeout_seconds,
        ) as smtp:
            if self.config.starttls:
                smtp.starttls()
            if self.config.username and self.config.password:
                smtp.login(self.config.username, self.config.password)
            smtp.send_message(message)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _key_hash(scope: str, value: str) -> str:
    normalized = value.strip().casefold()
    return hmac.new(
        settings.jwt_secret_key.encode(),
        f"password-reset:{scope}:{normalized}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _bucket(scope: str, key_hash: str, now: datetime, db: Session) -> AuthLoginThrottle:
    found = db.scalar(
        select(AuthLoginThrottle)
        .where(AuthLoginThrottle.scope == scope, AuthLoginThrottle.key_hash == key_hash)
        .with_for_update()
    )
    if found is not None:
        return found
    created = AuthLoginThrottle(
        scope=scope,
        key_hash=key_hash,
        attempt_count=0,
        window_started_at=now,
    )
    try:
        with db.begin_nested():
            db.add(created)
            db.flush()
        return created
    except IntegrityError:
        concurrent = db.scalar(
            select(AuthLoginThrottle)
            .where(AuthLoginThrottle.scope == scope, AuthLoginThrottle.key_hash == key_hash)
            .with_for_update()
        )
        if concurrent is None:
            raise
        return concurrent


def _consume_quota(email: str, origin: str, now: datetime, db: Session) -> bool:
    allowed = True
    for scope, value in ((_IDENTITY_SCOPE, email), (_ORIGIN_SCOPE, origin)):
        bucket = _bucket(scope, _key_hash(scope, value), now, db)
        if now - _utc(bucket.window_started_at) >= RESET_THROTTLE_WINDOW:
            bucket.attempt_count = 0
            bucket.window_started_at = now
            bucket.blocked_until = None
        if bucket.attempt_count >= RESET_THROTTLE_LIMIT:
            allowed = False
        else:
            bucket.attempt_count += 1
    db.commit()
    return allowed


def request_password_reset(
    email: str,
    origin: str,
    reset_base_url: str,
    sender: PasswordResetSender,
    db: Session,
    *,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    normalized_email = email.strip().casefold()
    db.execute(
        delete(AuthLoginThrottle).where(
            AuthLoginThrottle.scope.in_((_IDENTITY_SCOPE, _ORIGIN_SCOPE)),
            AuthLoginThrottle.window_started_at < current_time - timedelta(days=1),
        ).execution_options(synchronize_session=False)
    )
    db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.expires_at < current_time - timedelta(days=1)
        ).execution_options(synchronize_session=False)
    )
    db.commit()
    if not _consume_quota(normalized_email, origin, current_time, db):
        return

    user = db.scalar(select(User).where(User.email == normalized_email, User.active.is_(True)))
    if user is None:
        return

    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=current_time)
        .execution_options(synchronize_session=False)
    )
    raw_token = secrets.token_urlsafe(32)
    token = PasswordResetToken(
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        user_id=user.id,
        expires_at=current_time + RESET_TOKEN_TTL,
    )
    db.add(token)
    db.commit()

    separator = "&" if "?" in reset_base_url else "?"
    reset_url = f"{reset_base_url}{separator}reset_token={raw_token}"
    try:
        sender.send(user.email, reset_url)
    except Exception:
        token.used_at = current_time
        db.commit()
        logger.exception("Falha sanitizada ao enviar recuperação de senha")


def confirm_password_reset(
    raw_token: str,
    new_password: str,
    db: Session,
    *,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(UTC)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = db.scalar(
        select(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
        )
        .with_for_update()
    )
    if token is None or _utc(token.expires_at) <= current_time:
        raise PasswordResetRejected
    user = db.get(User, token.user_id)
    if user is None or not user.active or verify_password(new_password, user.password_hash):
        raise PasswordResetRejected

    user.password_hash = hash_password(new_password)
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=current_time)
        .execution_options(synchronize_session=False)
    )
    db.commit()
