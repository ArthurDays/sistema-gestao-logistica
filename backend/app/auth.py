import uuid
from collections.abc import Callable
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token, verify_password
from app.db import get_db
from app.models import User

security_scheme = HTTPBearer(auto_error=True)
current_organization: ContextVar[uuid.UUID] = ContextVar("current_organization")


@dataclass(frozen=True)
class CurrentUser:
    id: uuid.UUID
    organization_id: uuid.UUID
    role: str


def authenticate(email: str, password: str, db: Session) -> User | None:
    user = db.scalar(select(User).where(User.email == email.casefold(), User.active.is_(True)))
    return user if user and verify_password(password, user.password_hash) else None


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
