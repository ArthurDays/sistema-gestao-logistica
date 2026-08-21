from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Organization, User


def test_domain_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/vehicles", headers={"Authorization": ""})
    assert response.status_code == 403


def test_token_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/token",
        json={"email": "admin@teste.local", "password": "senha-incorreta"},
    )
    assert response.status_code == 401


def test_authenticated_user_can_read_current_session(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "admin@teste.local"
    assert response.json()["organization_name"] == "Teste"
    assert response.json()["role"] == "admin"


# SPECSFY: US-007 FR-017
def test_registration_creates_tenant_admin_and_authenticated_session(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Transportadora Horizonte",
            "email": "GESTOR@HORIZONTE.COM",
            "password": "senha-forte-123",
        },
    )

    assert response.status_code == 201
    session = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert session.status_code == 200
    assert session.json()["organization_name"] == "Transportadora Horizonte"
    assert session.json()["email"] == "gestor@horizonte.com"
    assert session.json()["role"] == "admin"


# SPECSFY: US-007 FR-017
def test_registration_rejects_duplicate_email_without_orphan_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    payload = {
        "organization_name": "Primeira Empresa",
        "email": "novo@empresa.com",
        "password": "senha-forte-123",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201

    duplicate = client.post(
        "/api/v1/auth/register",
        json={**payload, "organization_name": "Empresa Órfã", "email": "NOVO@EMPRESA.COM"},
    )

    assert duplicate.status_code == 409
    assert db_session.scalar(select(func.count()).select_from(Organization)) == 2
    assert db_session.scalar(select(func.count()).select_from(User)) == 2


# SPECSFY: US-007 FR-017
def test_registration_rejects_short_password_without_writes(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Cadastro Inválido",
            "email": "invalido@empresa.com",
            "password": "curta",
        },
    )

    assert response.status_code == 422
    assert db_session.scalar(select(func.count()).select_from(Organization)) == 1
    assert db_session.scalar(select(func.count()).select_from(User)) == 1
