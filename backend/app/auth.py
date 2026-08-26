import hashlib
import hmac
import math
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token, hash_password, verify_password
from app.db import get_db
from app.models import AuthLoginThrottle, User

security_scheme = HTTPBearer(auto_error=True)
current_organization: ContextVar[uuid.UUID] = ContextVar("current_organization")
_DUMMY_PASSWORD_HASH = hash_password("credencial-inexistente", salt="dummy-auth-salt-v1")
_LOGIN_WINDOW = timedelta(minutes=15)
_LOGIN_BLOCK = timedelta(minutes=15)
_LOGIN_MAX_FAILURES = 5


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    organization_id: uuid.UUID
    role: str


class AuthenticationThrottled(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("Limite temporário de autenticação atingido")


def authenticate(email: str, password: str, db: Session) -> User | None:
    user = db.scalar(select(User).where(User.email == email.casefold(), User.active.is_(True)))
    password_matches = verify_password(password, user.password_hash if user else _DUMMY_PASSWORD_HASH)
    return user if user and password_matches else None


def _throttle_key(scope: str, value: str) -> str:
    normalized = value.strip().casefold()
    return hmac.new(
        settings.jwt_secret_key.encode(),
        f"{scope}:{normalized}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _find_bucket(scope: str, key_hash: str, db: Session) -> AuthLoginThrottle | None:
    return db.scalar(
        select(AuthLoginThrottle)
        .where(AuthLoginThrottle.scope == scope, AuthLoginThrottle.key_hash == key_hash)
        .with_for_update()
    )


def _get_or_create_bucket(
    scope: str,
    key_hash: str,
    now: datetime,
    db: Session,
) -> AuthLoginThrottle:
    bucket = _find_bucket(scope, key_hash, db)
    if bucket is not None:
        return bucket
    bucket = AuthLoginThrottle(
        scope=scope,
        key_hash=key_hash,
        attempt_count=0,
        window_started_at=now,
    )
    try:
        with db.begin_nested():
            db.add(bucket)
            db.flush()
        return bucket
    except IntegrityError:
        concurrent_bucket = _find_bucket(scope, key_hash, db)
        if concurrent_bucket is None:
            raise
        return concurrent_bucket


def _active_retry_after(bucket: AuthLoginThrottle | None, now: datetime) -> int:
    if bucket is None or bucket.blocked_until is None:
        return 0
    remaining = (_as_utc(bucket.blocked_until) - now).total_seconds()
    return max(0, math.ceil(remaining))


def authenticate_with_throttle(
    email: str,
    password: str,
    source: str,
    db: Session,
) -> User | None:
    now = datetime.now(UTC)
    db.execute(
        delete(AuthLoginThrottle)
        .where(
            AuthLoginThrottle.window_started_at < now - timedelta(days=1),
            or_(
                AuthLoginThrottle.blocked_until.is_(None),
                AuthLoginThrottle.blocked_until < now,
            ),
        )
        .execution_options(synchronize_session=False)
    )
    db.commit()
    bucket_keys = (
        ("identity", _throttle_key("identity", email)),
        ("source", _throttle_key("source", source)),
    )
    buckets = {scope: _find_bucket(scope, key_hash, db) for scope, key_hash in bucket_keys}
    identity_retry_after = _active_retry_after(buckets["identity"], now)
    if identity_retry_after:
        raise AuthenticationThrottled(identity_retry_after)

    user = authenticate(email, password, db)
    if user is not None:
        identity_bucket = buckets["identity"]
        if identity_bucket is not None:
            db.delete(identity_bucket)
        db.commit()
        return user

    source_retry_after = _active_retry_after(buckets["source"], now)
    if source_retry_after:
        raise AuthenticationThrottled(source_retry_after)

    retry_after = 0
    for scope, key_hash in bucket_keys:
        bucket = buckets[scope] or _get_or_create_bucket(scope, key_hash, now, db)
        if now - _as_utc(bucket.window_started_at) >= _LOGIN_WINDOW:
            bucket.attempt_count = 0
            bucket.window_started_at = now
            bucket.blocked_until = None
        bucket.attempt_count += 1
        if bucket.attempt_count >= _LOGIN_MAX_FAILURES:
            bucket.blocked_until = now + _LOGIN_BLOCK
            retry_after = max(retry_after, math.ceil(_LOGIN_BLOCK.total_seconds()))
    db.commit()
    if retry_after:
        raise AuthenticationThrottled(retry_after)
    return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    claims = decode_access_token(credentials.credentials)
    try:
        user_id = uuid.UUID(str(claims["sub"]))
        organization_id = uuid.UUID(str(claims["organization_id"]))
        role = str(claims["role"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from None
    user = db.get(User, user_id)
    if user is None or not user.active or user.organization_id != organization_id or user.role != role:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    current_organization.set(user.organization_id)
    return CurrentUser(id=user.id, organization_id=user.organization_id, role=user.role)


def current_organization_id() -> uuid.UUID:
    try:
        return current_organization.get()
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação obrigatória",
        ) from None


def require_roles(*roles: str) -> Callable[[CurrentUser], CurrentUser]:
    def dependency(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permissão insuficiente")
        return user
    return dependency
