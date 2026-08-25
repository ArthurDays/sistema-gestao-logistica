from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260821_0009_bi_views.py"
)


def test_bi_migration_exposes_only_expected_read_models() -> None:
    migration = run_path(str(MIGRATION_PATH))
    statements: list[str] = []
    migration["upgrade"].__globals__["op"] = SimpleNamespace(execute=statements.append)

    migration["upgrade"]()

    sql = "\n".join(statements)
    assert "CREATE VIEW bi_vehicle_daily" in sql
    assert "CREATE VIEW bi_maintenance_alerts" in sql
    assert "GRANT SELECT ON bi_vehicle_daily, bi_maintenance_alerts TO metabase_bi" in sql
    assert "GRANT INSERT" not in sql
    assert "GRANT UPDATE" not in sql
    assert "GRANT DELETE" not in sql


def test_bi_migration_drops_views_in_dependency_safe_order() -> None:
    migration = run_path(str(MIGRATION_PATH))
    statements: list[str] = []
    migration["downgrade"].__globals__["op"] = SimpleNamespace(execute=statements.append)

    migration["downgrade"]()

    assert statements == ["DROP VIEW bi_maintenance_alerts", "DROP VIEW bi_vehicle_daily"]
