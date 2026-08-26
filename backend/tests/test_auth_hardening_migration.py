from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260825_0011_auth_hardening.py"
)


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-004
def test_auth_hardening_migration_creates_hashed_oauth_exchange_state() -> None:
    assert MIGRATION_PATH.is_file()
    migration = run_path(str(MIGRATION_PATH))
    operations: list[tuple[str, tuple[object, ...]]] = []
    fake_op = SimpleNamespace(
        create_table=lambda name, *items: operations.append((f"create:{name}", items)),
        create_index=lambda name, *items, **kwargs: operations.append((f"index:{name}", items)),
    )
    migration["upgrade"].__globals__["op"] = fake_op

    migration["upgrade"]()

    oauth_items = next(items for name, items in operations if name == "create:oauth_exchange_codes")
    column_names = {getattr(item, "name", None) for item in oauth_items}
    assert "code_hash" in column_names
    assert "code" not in column_names
    assert {"expires_at", "used_at", "user_id"} <= column_names


# SPECSFY: US-001 FR-001 FR-002 FR-003 FR-004 NFR-001 NFR-002 NFR-003 NFR-004 AC-005
def test_auth_hardening_migration_creates_hashed_login_throttle_state() -> None:
    assert MIGRATION_PATH.is_file()
    migration = run_path(str(MIGRATION_PATH))
    tables: list[tuple[str, tuple[object, ...]]] = []
    fake_op = SimpleNamespace(
        create_table=lambda name, *items: tables.append((name, items)),
        create_index=lambda *args, **kwargs: None,
    )
    migration["upgrade"].__globals__["op"] = fake_op

    migration["upgrade"]()

    throttle_items = next(items for name, items in tables if name == "auth_login_throttles")
    column_names = {getattr(item, "name", None) for item in throttle_items}
    assert {"scope", "key_hash", "attempt_count", "window_started_at", "blocked_until"} <= column_names
    assert "email" not in column_names
    assert "ip_address" not in column_names
