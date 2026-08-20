from fastapi.testclient import TestClient


def test_domain_routes_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/vehicles", headers={"Authorization": ""})
    assert response.status_code == 403


def test_token_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/token",
        json={"email": "admin@teste.local", "password": "senha-incorreta"},
    )
    assert response.status_code == 401
