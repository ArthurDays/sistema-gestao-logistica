from fastapi.testclient import TestClient


def create_vehicle(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Moto 01",
            "category": "motorcycle",
            "energy_type": "gasoline",
            "odometer_km": "10000.00",
            "tank_capacity": "12.00",
            "average_consumption": "35.000",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_register_operation_updates_odometer_and_is_idempotent(client: TestClient) -> None:
    vehicle = create_vehicle(client)
    payload = {
        "operation_date": "2026-08-17",
        "odometer_end_km": "10120.00",
        "gross_revenue": "350.00",
        "fuel_cost": "70.00",
    }
    headers = {"Idempotency-Key": "operation-20260817-moto01"}

    first = client.post(f"/api/v1/vehicles/{vehicle['id']}/operations", json=payload, headers=headers)
    repeated = client.post(f"/api/v1/vehicles/{vehicle['id']}/operations", json=payload, headers=headers)

    assert first.status_code == 201
    assert first.json()["odometer_start_km"] == "10000.00"
    assert first.json()["odometer_end_km"] == "10120.00"
    assert first.json()["distance_km"] == "120.00"
    assert first.json()["fuel_cost"] == "70.00"
    assert first.json()["fuel_cost_source"] == "informed"
    assert first.json()["maintenance_cost"] == "0.00"
    assert first.json()["net_profit"] == "280.00"
    assert repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    vehicles = client.get("/api/v1/vehicles").json()
    assert vehicles[0]["odometer_km"] == "10120.00"


def test_rejects_odometer_regression(client: TestClient) -> None:
    vehicle = create_vehicle(client)
    response = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={"operation_date": "2026-08-17", "odometer_end_km": "9999.00"},
        headers={"Idempotency-Key": "invalid-operation-0001"},
    )

    assert response.status_code == 422
    assert "menor" in response.json()["detail"]


def test_calculates_fuel_maintenance_and_real_profit(client: TestClient) -> None:
    vehicle = create_vehicle(client)
    rule = client.post(
        "/api/v1/maintenance-rules",
        json={
            "vehicle_id": vehicle["id"],
            "name": "Revisão programada",
            "interval_km": "1000.00",
            "estimated_cost": "200.00",
            "warning_km": "50.00",
        },
    )
    assert rule.status_code == 201

    response = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-17",
            "odometer_end_km": "10100.00",
            "gross_revenue": "300.00",
            "fuel_cost": None,
        },
        headers={"Idempotency-Key": "auto-cost-operation-0001"},
    )

    assert response.status_code == 201
    operation = response.json()
    assert operation["distance_km"] == "100.00"
    assert operation["fuel_cost"] == "17.14"
    assert operation["fuel_cost_source"] == "calculated"
    assert operation["fuel_unit_price"] == "6.000"
    assert operation["maintenance_cost"] == "20.00"
    assert operation["net_profit"] == "262.86"

    summary = client.get(
        "/api/v1/dashboard/monthly-summary",
        params={"reference_date": "2026-08-17"},
    )
    assert summary.status_code == 200
    assert summary.json() == {
        "date_from": "2026-08-01",
        "date_to": "2026-08-31",
        "gross_revenue": "300.00",
        "fuel_cost": "17.14",
        "maintenance_cost": "20.00",
        "net_profit": "262.86",
    }

    expense = client.post(
        "/api/v1/expenses",
        json={
            "vehicle_id": vehicle["id"],
            "expense_date": "2026-08-17",
            "category": "toll",
            "amount": "20.00",
            "description": "Pedágio do turno",
        },
    )
    assert expense.status_code == 201
    sampling = client.get(
        "/api/v1/dashboard/expense-sampling",
        params={"reference_date": "2026-08-17"},
    )
    assert sampling.status_code == 200
    periods = sampling.json()["periods"]
    assert [period["period"] for period in periods] == ["day", "week", "month"]
    assert periods[2]["total_cost"] == "57.14"
    assert periods[2]["fuel_percent"] == "30.00"
    assert periods[2]["maintenance_percent"] == "35.00"
    assert periods[2]["other_percent"] == "35.00"


def test_requires_consumption_when_fuel_cost_is_not_informed(client: TestClient) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Veículo sem consumo",
            "category": "car",
            "energy_type": "gasoline",
            "odometer_km": "100.00",
        },
    ).json()
    response = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-17",
            "odometer_end_km": "120.00",
            "gross_revenue": "100.00",
            "fuel_cost": "0.00",
        },
        headers={"Idempotency-Key": "missing-consumption-0001"},
    )

    assert response.status_code == 422
    assert "consumo médio" in response.json()["detail"]
