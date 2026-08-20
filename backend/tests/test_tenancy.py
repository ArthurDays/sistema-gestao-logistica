from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models import Organization, User


def test_organization_cannot_read_another_organizations_vehicle(
    client: TestClient, db_session: Session
) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Veículo privado",
            "category": "car",
            "energy_type": "gasoline",
            "odometer_km": "10",
        },
    ).json()
    organization = Organization(id=uuid4(), name="Outra organização")
    user = User(
        organization_id=organization.id,
        email="gestor@outra.local",
        password_hash=hash_password("senha-segura-para-testes"),
        role="manager",
    )
    db_session.add_all([organization, user])
    db_session.commit()
    token = create_access_token(str(user.id), str(organization.id), user.role)
    response = client.get(
        f"/api/v1/vehicles/{vehicle['id']}/profitability",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
    assert client.get("/api/v1/vehicles", headers={"Authorization": f"Bearer {token}"}).json() == []


def test_operator_cannot_create_vehicle(client: TestClient, db_session: Session) -> None:
    admin = db_session.scalar(select(User).where(User.role == "admin"))
    assert admin is not None
    user = User(
        organization_id=admin.organization_id,
        email="operador@teste.local",
        password_hash=hash_password("senha-segura-para-testes"),
        role="operator",
    )
    db_session.add(user)
    db_session.commit()
    token = create_access_token(str(user.id), str(user.organization_id), user.role)
    response = client.post(
        "/api/v1/vehicles",
        json={"name": "Não permitido", "category": "car", "energy_type": "gasoline", "odometer_km": "0"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
