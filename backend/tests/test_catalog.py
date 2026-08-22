import csv
from decimal import Decimal
from io import StringIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.catalog import parse_catalog
from app.models import MaintenanceRule, VehicleCatalogSpec

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


def catalog_csv(*rows: list[str]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([*CATALOG_HEADER, "", ""])
    writer.writerows(rows)
    return output.getvalue()


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


def test_parse_catalog_normalizes_omitted_category_and_split_decimal_values() -> None:
    csv_text = catalog_csv(
        [
            "Carro", "Volkswagen", "Gol", "1.0", "76 cv", "2025/2025", "Flex (Gasolina/Etanol)",
            "13.0", "9.1", "55.0", "330.0", "10000", "250.0", "40000",
        ],
        [
            "Chevrolet", "Onix", "1.0 Turbo", "116 cv", "2025/2025", "Flex (Gasolina/Etanol)",
            "13.5", "9.4", "44.0", "264.0", "10000", "320.0", "40000",
        ],
        [
            "Moto", "Honda", "CG 160", "Start", "162\\", "7 cm³ / 14\\", "9 cv", "2025/2025",
            "Gasolina", "41.0", "0.0", "14.6", "87.6", "6000", "180.0", "15000",
        ],
    )

    parsed = parse_catalog(csv_text)

    assert [row["category"] for row in parsed] == ["Carro", "Carro", "Moto"]
    assert parsed[1]["brand"] == "Chevrolet"
    assert parsed[1]["model"] == "Onix"
    assert parsed[2]["powertrain"] == "162,7 cm³ / 14,9 cv"
    assert parsed[2]["gasoline_consumption_km_l"] == Decimal("41.0")


def test_parse_catalog_rejects_ambiguous_row_before_writing() -> None:
    csv_text = catalog_csv(
        [
            "Marca sem categoria", "Modelo", "Versão", "Motor", "2025/2025", "Gasolina",
            "10.0", "0.0", "50.0", "300.0", "10000", "250.0", "40000",
        ]
    )

    with pytest.raises(ValueError, match="linha 2"):
        parse_catalog(csv_text)


def test_register_electric_bus_from_catalog(client: TestClient, db_session: Session) -> None:
    spec = VehicleCatalogSpec(
        category="Ônibus",
        brand="BYD",
        model="D9W",
        version="Elétrico Urbano",
        powertrain="80 passageiros",
        model_year="2025/2025",
        fuel_type="Elétrico",
        gasoline_consumption_km_l=None,
        ethanol_consumption_km_l=None,
        tank_capacity_l=None,
        estimated_tank_cost=None,
        oil_change_km=None,
        oil_change_cost=None,
        tire_change_km=75000,
    )
    db_session.add(spec)
    db_session.commit()

    response = client.post(
        f"/api/v1/vehicle-catalog/{spec.id}/register",
        json={"name": "Ônibus elétrico 01", "odometer_km": "0"},
    )

    assert response.status_code == 201
    assert response.json()["category"] == "bus"
    assert response.json()["energy_type"] == "electric"
