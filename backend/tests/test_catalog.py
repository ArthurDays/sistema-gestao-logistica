from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import parse_catalog
from app.models import MaintenanceRule, VehicleCatalogSpec


def test_parse_catalog_and_expose_specs(client: TestClient, db_session: Session) -> None:
    csv_text = (
        '"Categoria","Marca","Modelo Base","Versão / Trim Exato",'
        '"Motorização / Câmbio","Ano/Modelo","Combustível",'
        '"Consumo Gasolina (km/l)","Consumo Álcool (km/l)","Tanque (L)",'
        '"Custo Tanque Est. (Gas)","Troca Óleo (km)","Custo Óleo (R$)",'
        '"Troca Pneu (km)"\n'
        '"Moto","Honda","CG 160","Start","162.7 cc Single","2025/2025",'
        '"Gasolina","41.0","","14.6","87.60","3000","60.00","15000"\n'
    )
    parsed = parse_catalog(csv_text)
    assert len(parsed) == 1
    assert parsed[0]["gasoline_consumption_km_l"] == Decimal("41.0")
    assert parsed[0]["oil_change_km"] == 3000

    db_session.add(VehicleCatalogSpec(**parsed[0]))
    db_session.commit()
    response = client.get("/api/v1/vehicle-catalog")
    assert response.status_code == 200
    assert response.json()[0]["brand"] == "Honda"
    assert response.json()[0]["model"] == "CG 160"

    registration = client.post(
        f"/api/v1/vehicle-catalog/{response.json()[0]['id']}/register",
        json={"name": "Moto Entrega 01", "plate": "ABC1D23", "odometer_km": "125.00"},
    )
    assert registration.status_code == 201
    vehicle = registration.json()
    assert vehicle["catalog_spec_id"] == response.json()[0]["id"]
    assert vehicle["plate"] == "ABC1D23"
    assert vehicle["odometer_km"] == "125.00"
    assert vehicle["average_consumption"] == "41.000"
    assert db_session.scalar(select(func.count(MaintenanceRule.id))) == 2
