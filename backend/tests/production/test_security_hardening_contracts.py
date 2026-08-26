from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
COMPOSE = PROJECT_ROOT / "docker-compose.yml"
RUNBOOK = PROJECT_ROOT / "docs" / "runbook.md"
DOCKERFILE = PROJECT_ROOT / "backend" / "Dockerfile"
ROLE_INITIALIZER = PROJECT_ROOT / "infra" / "postgres" / "init-bi.sh"
PRODUCTION_ENV = PROJECT_ROOT / "infra" / "hosting" / "production.env.example"


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-006
def test_postgres_requires_external_password_and_binds_only_to_loopback() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")

    assert "POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?" in compose
    assert '127.0.0.1:${POSTGRES_PORT:-5432}:5432' in compose
    assert "POSTGRES_PASSWORD:-logistica" not in compose


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-006
def test_metabase_is_an_explicit_local_administrative_tool() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8").casefold()

    assert '127.0.0.1:${METABASE_PORT:-3001}:3000' in compose
    assert "administrativ" in runbook
    assert "tenant-facing" in runbook


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-006
def test_compose_never_publishes_administrative_services_on_all_interfaces() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")

    assert '      - "${POSTGRES_PORT:-5432}:5432"' not in compose
    assert '      - "${METABASE_PORT:-3001}:3000"' not in compose


# SPECSFY: US-001 FR-004 NFR-001 NFR-004 AC-005 AC-006
def test_runtime_does_not_trust_caller_controlled_forwarded_ip_headers() -> None:
    dockerfile = DOCKERFILE.read_text(encoding="utf-8")
    production_env = PRODUCTION_ENV.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")

    assert "--no-proxy-headers" in dockerfile
    assert "--forwarded-allow-ips" not in dockerfile
    assert "FORWARDED_ALLOW_IPS" not in production_env
    assert "não confia em cabeçalhos de origem encaminhados" in runbook


# SPECSFY: US-001 FR-004 NFR-001 AC-006
def test_domain_services_do_not_use_postgres_bootstrap_superuser() -> None:
    compose = COMPOSE.read_text(encoding="utf-8")
    initializer = ROLE_INITIALIZER.read_text(encoding="utf-8")

    assert "DOMAIN_APP_PASSWORD: ${DOMAIN_APP_PASSWORD:?" in compose
    assert "postgresql+psycopg://${DOMAIN_APP_USER:-logistica_app}" in compose
    assert "postgresql+psycopg://${POSTGRES_USER" not in compose
    assert "NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION" in initializer
