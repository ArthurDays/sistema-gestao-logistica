import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import api as api_module
from app import auth as auth_module
from app.core.config import settings
from app.models import AuthLoginThrottle, OAuthExchangeCode, User


def _configure_google(monkeypatch) -> None:
    monkeypatch.setattr(settings, "google_oauth_client_id", "client-id")
    monkeypatch.setattr(settings, "google_oauth_client_secret", "client-secret")
    monkeypatch.setattr(settings, "google_oauth_redirect_uri", "https://api.example.test/callback")
    monkeypatch.setattr(settings, "oauth_cookie_secure", False)


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-004
def test_google_oauth_sets_browser_correlation_cookie(client: TestClient, monkeypatch) -> None:
    _configure_google(monkeypatch)

    response = client.get("/api/v1/auth/google", follow_redirects=False)

    assert response.status_code == 307
    cookie = response.headers.get("set-cookie", "")
    assert "oauth_correlation=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-004
def test_google_oauth_state_cannot_be_used_by_another_browser(client: TestClient, monkeypatch) -> None:
    _configure_google(monkeypatch)

    class FakeResponse:
        def __init__(self, payload: dict[str, object]) -> None:
            self.payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return self.payload

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args) -> None:
            return None

        async def post(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse({"access_token": "google-access-token"})

        async def get(self, *args, **kwargs) -> FakeResponse:
            return FakeResponse(
                {
                    "email_verified": True,
                    "sub": "google-subject",
                    "email": "admin@teste.local",
                }
            )

    monkeypatch.setattr(api_module.httpx, "AsyncClient", FakeAsyncClient)
    started = client.get("/api/v1/auth/google", follow_redirects=False)
    state = parse_qs(urlparse(started.headers["location"]).query)["state"][0]

    foreign_browser = TestClient(client.app)
    response = foreign_browser.get(
        "/api/v1/auth/google/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )

    assert response.status_code == 401

    legitimate = client.get(
        "/api/v1/auth/google/callback",
        params={"code": "authorization-code", "state": state},
        follow_redirects=False,
    )
    redirect_query = parse_qs(urlparse(legitimate.headers["location"]).query)
    assert legitimate.status_code == 307
    assert "auth_code" in redirect_query
    assert "access_token" not in redirect_query


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-004
def test_oauth_exchange_endpoint_rejects_unknown_code_without_jwt_in_url(client: TestClient) -> None:
    response = client.post("/api/v1/auth/exchange", json={"code": "unknown-one-time-code"})

    assert response.status_code == 401
    assert b"access_token" not in response.request.url.query


# SPECSFY: US-001 FR-004 NFR-004 AC-004
def test_oauth_exchange_code_is_single_use(
    client: TestClient,
    db_session: Session,
) -> None:
    raw_code = "one-time-code-with-enough-entropy-for-test"
    user = db_session.query(User).filter_by(email="admin@teste.local").one()
    stale = OAuthExchangeCode(
        code_hash=hashlib.sha256(b"stale-one-time-code").hexdigest(),
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(stale)
    db_session.add(
        OAuthExchangeCode(
            code_hash=hashlib.sha256(raw_code.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=2),
        )
    )
    db_session.commit()
    stale_id = stale.id

    first = client.post("/api/v1/auth/exchange", json={"code": raw_code})
    replay = client.post("/api/v1/auth/exchange", json={"code": raw_code})

    assert first.status_code == 200
    assert replay.status_code == 401
    db_session.expire_all()
    assert db_session.get(OAuthExchangeCode, stale_id) is None


# SPECSFY: US-001 FR-004 NFR-004 AC-004
def test_invalid_oauth_exchange_still_commits_stale_code_cleanup(
    client: TestClient,
    db_session: Session,
) -> None:
    user = db_session.query(User).filter_by(email="admin@teste.local").one()
    stale = OAuthExchangeCode(
        code_hash=hashlib.sha256(b"stale-invalid-exchange").hexdigest(),
        user_id=user.id,
        expires_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(stale)
    db_session.commit()
    stale_id = stale.id

    response = client.post(
        "/api/v1/auth/exchange",
        json={"code": "unknown-code-with-enough-entropy-for-validation"},
    )

    assert response.status_code == 401
    db_session.rollback()
    db_session.expire_all()
    assert db_session.get(OAuthExchangeCode, stale_id) is None


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-005
def test_password_login_is_temporarily_blocked_after_five_failures(client: TestClient) -> None:
    payload = {"email": "admin@teste.local", "password": "senha-incorreta"}

    responses = [client.post("/api/v1/auth/token", json=payload) for _ in range(6)]

    assert [response.status_code for response in responses[:4]] == [401, 401, 401, 401]
    assert responses[4].status_code == 429
    assert responses[5].status_code == 429
    assert int(responses[5].headers["Retry-After"]) > 0


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-005
def test_password_login_limits_repeated_unknown_identities_from_same_source(client: TestClient) -> None:
    responses = [
        client.post(
            "/api/v1/auth/token",
            json={"email": f"unknown-{index}@example.test", "password": "senha-incorreta"},
        )
        for index in range(6)
    ]

    assert responses[-1].status_code == 429

    legitimate = client.post(
        "/api/v1/auth/token",
        json={"email": "admin@teste.local", "password": "senha-de-teste-segura"},
    )
    assert legitimate.status_code == 200


# SPECSFY: US-001 FR-004 NFR-004 AC-005
def test_password_login_recovers_after_temporary_block_expires(
    client: TestClient,
    db_session: Session,
) -> None:
    invalid = {"email": "admin@teste.local", "password": "senha-incorreta"}
    for _ in range(5):
        client.post("/api/v1/auth/token", json=invalid)
    expired_at = datetime.now(UTC) - timedelta(minutes=16)
    for bucket in db_session.query(AuthLoginThrottle).all():
        bucket.blocked_until = expired_at
        bucket.window_started_at = expired_at
    stale = AuthLoginThrottle(
        scope="source",
        key_hash="f" * 64,
        attempt_count=1,
        window_started_at=datetime.now(UTC) - timedelta(days=2),
    )
    db_session.add(stale)
    db_session.commit()
    stale_id = stale.id

    response = client.post(
        "/api/v1/auth/token",
        json={"email": "admin@teste.local", "password": "senha-de-teste-segura"},
    )

    assert response.status_code == 200
    db_session.expire_all()
    assert db_session.get(AuthLoginThrottle, stale_id) is None


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-005
def test_unknown_email_performs_equivalent_password_verification(
    db_session: Session,
    monkeypatch,
) -> None:
    calls: list[str] = []

    def record_verification(password: str, password_hash: str) -> bool:
        calls.append(password_hash)
        return False

    monkeypatch.setattr(auth_module, "verify_password", record_verification)

    auth_module.authenticate("unknown@example.test", "senha-incorreta", db_session)

    assert len(calls) == 1
    assert calls[0].startswith("pbkdf2_sha256$")


# SPECSFY: US-001 FR-004 NFR-001 AC-004
def test_frontend_does_not_consume_access_token_from_query_string() -> None:
    source = (
        Path(__file__).parents[2] / "frontend" / "components" / "operations-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert 'searchParams.get("access_token")' not in source
    assert 'searchParams.get("auth_code")' in source


def test_frontend_auth_state_is_deterministic_during_hydration() -> None:
    source = (
        Path(__file__).parents[2] / "frontend" / "components" / "operations-dashboard.tsx"
    ).read_text(encoding="utf-8")

    assert "const [authenticated, setAuthenticated] = useState(false);" in source
    assert "useState(() => typeof window" not in source
