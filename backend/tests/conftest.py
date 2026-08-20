import os
import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-long-enough-for-local-validation")

from app.core.security import hash_password
from app.db import Base, get_db
from app.main import app
from app.models import Organization, User

DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(Organization(id=DEFAULT_ORGANIZATION_ID, name="Teste"))
        session.add(User(
            organization_id=DEFAULT_ORGANIZATION_ID,
            email="admin@teste.local",
            password_hash=hash_password("senha-de-teste-segura"),
            role="admin",
        ))
        session.commit()
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as auth_client:
        token = auth_client.post(
            "/api/v1/auth/token",
            json={"email": "admin@teste.local", "password": "senha-de-teste-segura"},
        )
        assert token.status_code == 200
    with TestClient(app, headers={"Authorization": f"Bearer {token.json()['access_token']}"}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
