from fastapi.testclient import TestClient


def test_profitability_includes_fuel_and_categorized_expenses(client: TestClient) -> None:
    vehicle = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Caminhão 01",
            "category": "truck",
            "energy_type": "diesel",
            "odometer_km": "20000.00",
        },
    ).json()
    operation = client.post(
        f"/api/v1/vehicles/{vehicle['id']}/operations",
        json={
            "operation_date": "2026-08-17",
            "odometer_end_km": "20200.00",
            "gross_revenue": "1000.00",
            "fuel_cost": "300.00",
        },
        headers={"Idempotency-Key": "truck-operation-20260817"},
    )
    assert operation.status_code == 201
    expense = client.post(
        "/api/v1/expenses",
        json={
            "vehicle_id": vehicle["id"],
            "expense_date": "2026-08-17",
            "category": "toll",
            "amount": "50.00",
            "description": "Pedágio da rota",
        },
    )
    assert expense.status_code == 201

    response = client.get(
        f"/api/v1/vehicles/{vehicle['id']}/profitability",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["distance_km"] == "200.00"
    assert result["total_cost"] == "350.00"
    assert result["net_profit"] == "650.00"
    assert result["cost_per_km"] == "1.75"
    assert result["net_margin_percent"] == "65.00"
