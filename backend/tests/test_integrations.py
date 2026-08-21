import uuid
from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FuelPrice, IntegrationReceipt, Vehicle


def test_import_fuel_price_is_idempotent_and_auditable(client: TestClient, db_session: Session) -> None:
    payload = {
        "source": "anp",
        "locality": "Brasília/DF",
        "energy_type": "gasoline",
        "unit_price": "6.199",
        "effective_date": "2026-08-21",
    }
    headers = {"Idempotency-Key": "anp-brasilia-20260821-gasoline"}

    first = client.post("/api/v1/integrations/fuel-prices", json=payload, headers=headers)
    second = client.post("/api/v1/integrations/fuel-prices", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    fuel_prices = list(db_session.scalars(select(FuelPrice)))
    assert len(fuel_prices) == 1
    assert fuel_prices[0].unit_price == Decimal("6.199")
    assert fuel_prices[0].effective_date == date(2026, 8, 21)
    receipt = db_session.scalar(select(IntegrationReceipt))
    assert receipt is not None
    assert receipt.source == "anp"
    assert receipt.payload["locality"] == "Brasília/DF"


def test_import_vehicle_data_updates_only_own_vehicle(client: TestClient, db_session: Session) -> None:
    vehicle = Vehicle(
        organization_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        name="Moto de integração",
        category="motorcycle",
        energy_type="gasoline",
        odometer_km=Decimal("100"),
    )
    db_session.add(vehicle)
    db_session.commit()

    response = client.post(
        "/api/v1/integrations/vehicle-data",
        json={
            "source": "n8n",
            "vehicle_id": str(vehicle.id),
            "tank_capacity": "16.50",
            "average_consumption": "35.500",
        },
        headers={"Idempotency-Key": "n8n-moto-dados-20260821"},
    )

    assert response.status_code == 201
    db_session.refresh(vehicle)
    assert vehicle.tank_capacity == Decimal("16.50")
    assert vehicle.average_consumption == Decimal("35.500")
