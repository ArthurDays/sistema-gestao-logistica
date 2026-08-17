from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OutboxEvent


def test_maintenance_reserve_alert_and_execution_reset(
    client: TestClient,
    db_session: Session,
) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Moto Manutenção",
            "category": "motorcycle",
            "energy_type": "gasoline",
            "odometer_km": "10000.00",
        },
    ).json()
    rule_response = client.post(
        "/api/v1/maintenance-rules",
        json={
            "vehicle_id": vehicle["id"],
            "name": "Troca de óleo",
            "interval_km": "1000.00",
            "estimated_cost": "200.00",
            "warning_km": "100.00",
        },
    )
    assert rule_response.status_code == 201
    rule = rule_response.json()

    operation = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-17",
            "odometer_end_km": "10900.00",
            "gross_revenue": "1000.00",
            "fuel_cost": "100.00",
        },
        headers={"Idempotency-Key": "maintenance-operation-20260817"},
    )
    assert operation.status_code == 201

    alerts = client.get("/api/v1/maintenance-alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["due_odometer_km"] == "11000.00"

    profitability = client.get(
        f"/api/v1/vehicles/{vehicle['id']}/profitability",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    ).json()
    assert profitability["maintenance_reserve"] == "180.00"
    assert profitability["net_profit"] == "720.00"

    execution = client.post(
        f"/api/v1/maintenance-rules/{rule['id']}/executions",
        json={
            "performed_at": "2026-08-17",
            "odometer_km": "10900.00",
            "actual_cost": "190.00",
        },
    )
    assert execution.status_code == 201
    assert client.get("/api/v1/maintenance-alerts").json() == []
    assert db_session.scalar(select(func.count(OutboxEvent.id))) == 2


def test_date_threshold_wins_when_km_threshold_is_still_far_away(
    client: TestClient,
) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Caminhão por calendário",
            "category": "truck",
            "energy_type": "diesel",
            "odometer_km": "5000.00",
        },
    ).json()
    response = client.post(
        "/api/v1/maintenance-rules",
        json={
            "vehicle_id": vehicle["id"],
            "name": "Inspeção anual",
            "interval_km": "50000.00",
            "interval_days": 1,
            "estimated_cost": "500.00",
            "warning_km": "100.00",
            "warning_days": 1,
        },
    )

    assert response.status_code == 201
    alerts = client.get("/api/v1/maintenance-alerts").json()
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "warning"
    assert alerts[0]["due_odometer_km"] == "55000.00"
    assert alerts[0]["due_date"] == (date.today() + timedelta(days=1)).isoformat()
