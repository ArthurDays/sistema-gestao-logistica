import csv
import hashlib
import hmac
import json
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import parse_catalog
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models import (
    MaintenanceRule,
    Organization,
    OutboxEvent,
    User,
    VehicleCatalogSpec,
)
from app.outbox import deliver_pending_events

CATALOG_HEADER = [
    "Categoria",
    "Marca",
    "Modelo Base",
    "Versão / Trim Exato",
    "Motorização / Câmbio",
    "Ano/Modelo",
    "Combustível",
    "Consumo Gasolina (km/l)",
    "Consumo Álcool (km/l)",
    "Tanque (L)",
    "Custo Tanque Est. (Gas)",
    "Troca Óleo (km)",
    "Custo Óleo (R$)",
    "Troca Pneu (km)",
]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
FRONTEND_COMPONENT = PROJECT_ROOT / "frontend/components/operations-dashboard.tsx"
FRONTEND_GLOBALS = PROJECT_ROOT / "frontend/app/globals.css"


def _catalog_csv(*rows: list[str]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([*CATALOG_HEADER, "", ""])
    writer.writerows(rows)
    return output.getvalue()


def _create_vehicle(
    client: TestClient,
    *,
    name: str,
    odometer_km: str = "10000.00",
    category: str = "motorcycle",
    energy_type: str = "gasoline",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "name": name,
            "category": category,
            "energy_type": energy_type,
            "odometer_km": odometer_km,
            "tank_capacity": "12.00",
            "average_consumption": "35.000",
        },
    )
    assert response.status_code == 201
    return response.json()


# SPECSFY: US-001 FR-004 FR-005 FR-015 NFR-001 NFR-002 NFR-003 AC-001
def test_ac001_registers_valid_daily_closing_with_decimal_distance(client: TestClient) -> None:
    vehicle = _create_vehicle(client, name="Moto AC-001")

    response = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-25",
            "odometer_end_km": "10120.00",
            "gross_revenue": "350.00",
            "fuel_cost": "70.00",
        },
        headers={"Idempotency-Key": "spec-0001-ac001"},
    )

    assert response.status_code == 201
    result = response.json()
    assert Decimal(result["distance_km"]) == Decimal("120.00")
    assert Decimal(result["gross_revenue"]) == Decimal("350.00")
    assert Decimal(result["net_profit"]) == Decimal("280.00")


# SPECSFY: US-001 FR-004 FR-005 FR-015 NFR-001 NFR-002 NFR-003 AC-002
def test_ac002_rejects_odometer_regression_with_actionable_error(client: TestClient) -> None:
    vehicle = _create_vehicle(client, name="Moto AC-002")

    response = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={"operation_date": "2026-08-25", "odometer_end_km": "9999.00"},
        headers={"Idempotency-Key": "spec-0001-ac002"},
    )

    assert response.status_code == 422
    assert "menor" in response.json()["detail"]


# SPECSFY: US-001 FR-004 FR-005 FR-015 NFR-001 NFR-002 NFR-003 AC-003
def test_ac003_replay_returns_same_operation_without_duplicate(client: TestClient) -> None:
    vehicle = _create_vehicle(client, name="Moto AC-003")
    payload = {
        "operation_date": "2026-08-25",
        "odometer_end_km": "10100.00",
        "gross_revenue": "200.00",
        "fuel_cost": "40.00",
    }
    headers = {"Idempotency-Key": "spec-0001-ac003"}

    first = client.post(f"/api/v1/vehicles/{vehicle['id']}/operations", json=payload, headers=headers)
    replay = client.post(f"/api/v1/vehicles/{vehicle['id']}/operations", json=payload, headers=headers)

    assert first.status_code == replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]
    summary = client.get(
        "/api/v1/dashboard/monthly-summary",
        params={"reference_date": "2026-08-25"},
    )
    assert Decimal(summary.json()["gross_revenue"]) == Decimal("200.00")


# SPECSFY: US-002 FR-006 FR-007 FR-008 FR-013 FR-014 NFR-001 NFR-005 AC-004
def test_ac004_calculates_exact_real_net_profit(client: TestClient) -> None:
    vehicle = _create_vehicle(client, name="Carro AC-004", category="car")
    rule = client.post(
        "/api/v1/maintenance-rules",
        json={
            "vehicle_id": vehicle["id"],
            "name": "Reserva AC-004",
            "interval_km": "1000.00",
            "estimated_cost": "150.00",
            "warning_km": "50.00",
        },
    )
    assert rule.status_code == 201

    operation = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-25",
            "odometer_end_km": "10100.00",
            "gross_revenue": "350.00",
            "fuel_cost": "70.00",
        },
        headers={"Idempotency-Key": "spec-0001-ac004"},
    )

    assert operation.status_code == 201
    assert Decimal(operation.json()["maintenance_cost"]) == Decimal("15.00")
    assert Decimal(operation.json()["net_profit"]) == Decimal("265.00")


# SPECSFY: US-002 FR-006 FR-007 FR-008 FR-013 FR-014 NFR-001 NFR-005 AC-005
def test_ac005_applies_expense_only_to_configured_vehicle_and_period(client: TestClient) -> None:
    target = _create_vehicle(client, name="Carro AC-005 A", category="car")
    other = _create_vehicle(client, name="Carro AC-005 B", category="car")
    expenses = [
        (target["id"], "2026-08-15", "120.00", "Parcela aplicável"),
        (target["id"], "2026-07-31", "50.00", "Fora do período"),
        (other["id"], "2026-08-15", "80.00", "Outro veículo"),
    ]
    for vehicle_id, expense_date, amount, description in expenses:
        response = client.post(
            "/api/v1/expenses",
            json={
                "vehicle_id": vehicle_id,
                "expense_date": expense_date,
                "category": "insurance",
                "amount": amount,
                "description": description,
            },
        )
        assert response.status_code == 201

    profitability = client.get(
        f"/api/v1/vehicles/{target['id']}/profitability",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )

    assert profitability.status_code == 200
    assert Decimal(profitability.json()["other_expenses"]) == Decimal("120.00")


# SPECSFY: US-002 FR-006 FR-007 FR-008 FR-013 FR-014 NFR-001 NFR-005 AC-006
def test_ac006_preserves_historical_cost_and_responds_within_budget(
    client: TestClient,
    monkeypatch,
) -> None:
    vehicle = _create_vehicle(client, name="Carro AC-006", category="car")
    monkeypatch.setattr(settings, "base_fuel_price_per_liter", Decimal("6.00"))
    operation = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-25",
            "odometer_end_km": "10100.00",
            "gross_revenue": "300.00",
            "fuel_cost": None,
        },
        headers={"Idempotency-Key": "spec-0001-ac006"},
    )
    assert operation.status_code == 201
    original_cost = operation.json()["fuel_cost"]

    monkeypatch.setattr(settings, "base_fuel_price_per_liter", Decimal("9.99"))
    started = perf_counter()
    profitability = client.get(
        f"/api/v1/vehicles/{vehicle['id']}/profitability",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    elapsed = perf_counter() - started

    assert profitability.status_code == 200
    assert profitability.json()["fuel_cost"] == original_cost
    assert elapsed < 3


# SPECSFY: US-003 FR-009 FR-010 FR-011 FR-012 NFR-003 NFR-006 AC-007
def test_ac007_creates_warning_at_maintenance_threshold(client: TestClient) -> None:
    vehicle = _create_vehicle(client, name="Caminhão AC-007", category="truck", energy_type="diesel")
    rule = client.post(
        "/api/v1/maintenance-rules",
        json={
            "vehicle_id": vehicle["id"],
            "name": "Troca de óleo AC-007",
            "interval_km": "5000.00",
            "estimated_cost": "500.00",
            "warning_km": "500.00",
        },
    )
    assert rule.status_code == 201
    operation = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-25",
            "odometer_end_km": "14500.00",
            "gross_revenue": "1000.00",
            "fuel_cost": "300.00",
        },
        headers={"Idempotency-Key": "spec-0001-ac007"},
    )
    assert operation.status_code == 201

    alerts = client.get("/api/v1/maintenance-alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["due_odometer_km"] == "15000.00"


# SPECSFY: US-003 FR-009 FR-010 FR-011 FR-012 NFR-003 NFR-006 AC-008
def test_ac008_delivers_critical_event_once_with_hmac_signature(
    db_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(settings, "n8n_webhook_url", "https://n8n.test/webhook")
    monkeypatch.setattr(settings, "n8n_webhook_secret", "acceptance-secret")
    event = OutboxEvent(
        organization_id=uuid4(),
        event_type="maintenance.alert.critical",
        aggregate_type="maintenance_alert",
        aggregate_id=uuid4(),
        payload={"severity": "critical"},
        created_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.commit()
    captured: dict[str, object] = {}

    def sender(url: str, body: bytes, headers: dict[str, str]) -> None:
        captured.update(url=url, body=body, headers=headers)

    assert deliver_pending_events(db_session, sender) == 1
    assert deliver_pending_events(db_session, sender) == 0
    headers = captured["headers"]
    assert isinstance(headers, dict)
    expected = hmac.new(b"acceptance-secret", captured["body"], hashlib.sha256).hexdigest()
    assert headers["Idempotency-Key"] == str(event.id)
    assert headers["X-Logistica-Signature"] == f"sha256={expected}"
    assert json.loads(captured["body"])["payload"]["severity"] == "critical"


# SPECSFY: US-003 FR-009 FR-010 FR-011 FR-012 NFR-003 NFR-006 AC-009
def test_ac009_execution_closes_alert_and_restarts_cycle(client: TestClient) -> None:
    vehicle = _create_vehicle(client, name="Moto AC-009")
    rule = client.post(
        "/api/v1/maintenance-rules",
        json={
            "vehicle_id": vehicle["id"],
            "name": "Revisão AC-009",
            "interval_km": "1000.00",
            "estimated_cost": "200.00",
            "warning_km": "100.00",
        },
    ).json()
    operation = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-25",
            "odometer_end_km": "10950.00",
            "gross_revenue": "500.00",
            "fuel_cost": "100.00",
        },
        headers={"Idempotency-Key": "spec-0001-ac009"},
    )
    assert operation.status_code == 201
    assert len(client.get("/api/v1/maintenance-alerts").json()) == 1

    execution = client.post(
        f"/api/v1/maintenance-rules/{rule['id']}/executions",
        json={
            "performed_at": "2026-08-25",
            "odometer_km": "10950.00",
            "actual_cost": "190.00",
        },
    )

    assert execution.status_code == 201
    assert client.get("/api/v1/maintenance-alerts").json() == []


# SPECSFY: US-004 US-005 FR-002 FR-003 FR-012 FR-018 FR-019 FR-020 NFR-004 NFR-008 NFR-009 AC-010
def test_ac010_imports_valid_catalog_without_writing_to_source(
    client: TestClient,
    db_session: Session,
) -> None:
    csv_text = _catalog_csv(
        [
            "Moto", "Honda", "CG 160", "Start", "162.7 cc", "2025/2025", "Gasolina",
            "41.0", "", "14.6", "87.60", "3000", "60.00", "15000",
        ]
    )
    parsed = parse_catalog(csv_text)
    assert len(parsed) == 1
    db_session.add(VehicleCatalogSpec(**parsed[0]))
    db_session.commit()

    specs = client.get("/api/v1/vehicle-catalog")
    assert specs.status_code == 200
    registration = client.post(
        f"/api/v1/vehicle-catalog/{specs.json()[0]['id']}/register",
        json={"name": "Moto catálogo AC-010", "odometer_km": "0.00"},
    )

    assert registration.status_code == 201
    assert registration.json()["category"] == "motorcycle"
    assert db_session.scalar(select(func.count(MaintenanceRule.id))) == 2


# SPECSFY: US-004 US-005 FR-002 FR-003 FR-012 FR-018 FR-019 FR-020 NFR-004 NFR-008 NFR-009 AC-011
def test_ac011_inherits_only_omitted_category_and_preserves_decimals() -> None:
    csv_text = _catalog_csv(
        [
            "Carro", "Volkswagen", "Gol", "1.0", "76 cv", "2025/2025",
            "Flex (Gasolina/Etanol)", "13.0", "9.1", "55.0", "330.0", "10000", "250.0", "40000",
        ],
        [
            "Chevrolet", "Onix", "1.0 Turbo", "116 cv", "2025/2025",
            "Flex (Gasolina/Etanol)", "13.5", "9.4", "44.0", "264.0", "10000", "320.0", "40000",
        ],
    )

    parsed = parse_catalog(csv_text)

    assert [item["category"] for item in parsed] == ["Carro", "Carro"]
    assert parsed[1]["brand"] == "Chevrolet"
    assert parsed[1]["gasoline_consumption_km_l"] == Decimal("13.5")
    assert parsed[1]["ethanol_consumption_km_l"] == Decimal("9.4")


# SPECSFY: US-004 US-005 FR-002 FR-003 FR-012 FR-018 FR-019 FR-020 NFR-004 NFR-008 NFR-009 AC-012
def test_ac012_rejects_invalid_catalog_atomically(db_session: Session) -> None:
    initial_count = db_session.scalar(select(func.count(VehicleCatalogSpec.id)))
    csv_text = _catalog_csv(
        [
            "Marca sem categoria", "Modelo", "Versão", "Motor", "2025/2025",
            "Gasolina", "10.0", "0.0", "50.0", "300.0", "10000", "250.0", "40000",
        ]
    )

    with pytest.raises(ValueError, match="linha 2"):
        parsed = parse_catalog(csv_text)
        db_session.add_all(VehicleCatalogSpec(**item) for item in parsed)
        db_session.commit()

    assert db_session.scalar(select(func.count(VehicleCatalogSpec.id))) == initial_count


# SPECSFY: US-007 FR-001 FR-017 NFR-003 NFR-004 NFR-006 AC-013
def test_ac013_registers_tenant_and_returns_authenticated_admin(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Transportadora AC-013",
            "email": "owner.ac013@example.com",
            "password": "senha-segura-ac013",
        },
    )

    assert response.status_code == 201
    session = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {response.json()['access_token']}"},
    )
    assert session.status_code == 200
    assert session.json()["organization_name"] == "Transportadora AC-013"
    assert session.json()["email"] == "owner.ac013@example.com"
    assert session.json()["role"] == "admin"


# SPECSFY: US-007 FR-001 FR-017 NFR-003 NFR-004 NFR-006 AC-014
def test_ac014_rejects_duplicate_email_without_orphan_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    payload = {
        "organization_name": "Transportadora AC-014",
        "email": "owner.ac014@example.com",
        "password": "senha-segura-ac014",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    organization_count = db_session.scalar(select(func.count(Organization.id)))
    user_count = db_session.scalar(select(func.count(User.id)))

    duplicate = client.post(
        "/api/v1/auth/register",
        json={**payload, "organization_name": "Organização órfã", "email": "OWNER.AC014@EXAMPLE.COM"},
    )

    assert duplicate.status_code == 409
    assert db_session.scalar(select(func.count(Organization.id))) == organization_count
    assert db_session.scalar(select(func.count(User.id))) == user_count
    assert db_session.scalar(
        select(func.count(Organization.id)).where(Organization.name == "Organização órfã")
    ) == 0


# SPECSFY: US-007 FR-001 FR-017 NFR-003 NFR-004 NFR-006 AC-015
def test_ac015_isolates_vehicle_data_by_token_organization(
    client: TestClient,
    db_session: Session,
) -> None:
    vehicle = _create_vehicle(client, name="Veículo exclusivo AC-015")
    other_organization = Organization(name="Outro tenant AC-015")
    db_session.add(other_organization)
    db_session.flush()
    other_user = User(
        organization_id=other_organization.id,
        email="other.ac015@example.com",
        password_hash=hash_password("senha-segura-ac015"),
        role="admin",
    )
    db_session.add(other_user)
    db_session.commit()
    token = create_access_token(str(other_user.id), str(other_organization.id), other_user.role)
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/vehicles", headers=headers).json() == []
    profitability = client.get(
        f"/api/v1/vehicles/{vehicle['id']}/profitability",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
        headers=headers,
    )
    assert profitability.status_code == 404


# SPECSFY: US-006 FR-014 FR-016 NFR-005 NFR-007 AC-016
def test_ac016_mobile_shell_prevents_overflow_and_keeps_navigation_available() -> None:
    component = FRONTEND_COMPONENT.read_text(encoding="utf-8")
    globals_css = FRONTEND_GLOBALS.read_text(encoding="utf-8")
    routes = {
        "page.tsx": 'view="overview"',
        "frota/page.tsx": 'view="fleet"',
        "catalogo/page.tsx": 'view="catalog"',
        "financeiro/page.tsx": 'view="finances"',
    }

    assert "min-width: 320px" in globals_css
    assert "overflow-x: hidden" in globals_css
    assert 'aria-label="Navegação principal móvel"' in component
    assert "fixed inset-x-0 bottom-0" in component
    assert "min-h-14" in component
    assert "lg:hidden" in component
    for route, expected_view in routes.items():
        source = (PROJECT_ROOT / "frontend/app" / route).read_text(encoding="utf-8")
        assert expected_view in source


# SPECSFY: US-006 FR-014 FR-016 NFR-005 NFR-007 AC-017
def test_ac017_desktop_shell_exposes_sidebar_cards_filters_forms_and_actions() -> None:
    component = FRONTEND_COMPONENT.read_text(encoding="utf-8")

    assert "<DashboardSidebar" in component
    assert 'className="hidden w-full' in component
    assert "lg:pl-72" in component and "lg:pl-28" in component
    assert 'aria-label="Indicadores financeiros"' in component
    assert 'aria-label="Classificação da frota"' in component
    assert "categoryFilter" in component and "catalogSearch" in component
    assert "submitClosing" in component and "submitMaintenance" in component
    assert "submitVehicleRegistration" in component
    assert "Exportar frota" in component and "Lançar fechamento" in component


# SPECSFY: US-006 FR-014 FR-016 NFR-005 NFR-007 AC-018
def test_ac018_keyboard_focus_errors_confirmations_and_states_are_perceptible() -> None:
    component = FRONTEND_COMPONENT.read_text(encoding="utf-8")

    assert "focus:ring-2" in component
    assert 'role="alert"' in component
    assert 'aria-current={active ? "page" : undefined}' in component
    assert 'aria-label="Fechar painel"' in component
    assert "<FieldLabel" in component
    assert "min-h-11" in component
    assert "setLoading(true)" in component and "setLoading(false)" in component
    assert "Nenhum veículo nesta classificação." in component
    assert "Fechamento registrado:" in component
    assert "session?.role" in component
