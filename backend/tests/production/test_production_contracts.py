import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[3]
HOSTING_ENV = PROJECT_ROOT / "infra" / "hosting" / "production.env.example"
HOSTING_VALIDATOR = PROJECT_ROOT / "infra" / "hosting" / "validate-production-config.ps1"
BACKUP_SCRIPT = PROJECT_ROOT / "infra" / "postgres" / "backup.ps1"
RESTORE_SCRIPT = PROJECT_ROOT / "infra" / "postgres" / "restore-check.ps1"
RUNBOOK = PROJECT_ROOT / "docs" / "runbook.md"


# SPECSFY: US-001 FR-001 FR-002 FR-003 NFR-001 NFR-002 NFR-003 AC-001
def test_managed_hosting_contract_is_secure() -> None:
    assert HOSTING_ENV.is_file(), "infra/hosting/production.env.example deve declarar o contrato"
    assert HOSTING_VALIDATOR.is_file(), "o validador de configuração gerenciada deve existir"

    contract = HOSTING_ENV.read_text(encoding="utf-8")
    required_keys = {"FRONTEND_URL", "BACKEND_URL", "CORS_ORIGINS", "GOOGLE_REDIRECT_URI"}
    declared_keys = {
        line.split("=", 1)[0]
        for line in contract.splitlines()
        if line and not line.startswith("#") and "=" in line
    }

    assert required_keys <= declared_keys
    for line in contract.splitlines():
        if line.startswith(("FRONTEND_URL=", "BACKEND_URL=", "GOOGLE_REDIRECT_URI=")):
            assert line.split("=", 1)[1].startswith("https://")
    assert "*" not in next(line for line in contract.splitlines() if line.startswith("CORS_ORIGINS="))


# SPECSFY: US-001 FR-001 FR-002 FR-003 NFR-001 NFR-002 NFR-003 AC-002
def test_insecure_production_configuration_is_rejected() -> None:
    assert HOSTING_VALIDATOR.is_file(), "o gate deve rejeitar configuração insegura antes do deploy"

    validator = HOSTING_VALIDATOR.read_text(encoding="utf-8")
    assert re.search(r"https", validator, re.IGNORECASE), "o gate deve exigir HTTPS público"
    assert re.search(r"CORS|origin", validator, re.IGNORECASE), "o gate deve restringir origens"
    assert re.search(r"secret|senha|password|token", validator, re.IGNORECASE), (
        "o gate deve detectar segredo literal"
    )
    assert re.search(r"exit\s+1|throw", validator, re.IGNORECASE), "a configuração insegura deve falhar"


# SPECSFY: US-001 FR-001 FR-002 FR-003 NFR-001 NFR-002 NFR-003 AC-003
def test_recovery_contract_is_reproducible() -> None:
    required_artifacts = (BACKUP_SCRIPT, RESTORE_SCRIPT, RUNBOOK)
    missing = [str(path.relative_to(PROJECT_ROOT)) for path in required_artifacts if not path.is_file()]
    assert not missing, f"recuperação exige os artefatos ausentes: {', '.join(missing)}"

    backup = BACKUP_SCRIPT.read_text(encoding="utf-8")
    restore = RESTORE_SCRIPT.read_text(encoding="utf-8")
    runbook = RUNBOOK.read_text(encoding="utf-8")
    assert "pg_dump" in backup
    assert "pg_restore" in restore or "psql" in restore
    assert re.search(r"descart|isolad|temporary|temp", restore, re.IGNORECASE)
    for topic in ("backup", "restaura", "rollback", "health"):
        assert re.search(topic, runbook, re.IGNORECASE), f"runbook deve documentar {topic}"
