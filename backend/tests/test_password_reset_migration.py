from pathlib import Path
from runpy import run_path
from types import SimpleNamespace

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260826_0012_password_reset.py"
)


# SPECSFY: US-001 FR-002 FR-004 NFR-002 AC-001 AC-003 AC-004
def test_password_reset_migration_is_hash_only_indexed_and_reversible() -> None:
    assert MIGRATION_PATH.is_file()
    migration = run_path(str(MIGRATION_PATH))
    assert migration["revision"] == "20260826_0012"
    assert migration["down_revision"] == "20260825_0011"
    operations: list[tuple[str, str, tuple[object, ...]]] = []
    fake_op = SimpleNamespace(
        create_table=lambda name, *items: operations.append(("create_table", name, items)),
        create_index=lambda name, table, columns, **_kwargs: operations.append(
            ("create_index", name, (table, *columns))
        ),
        drop_index=lambda name, **_kwargs: operations.append(("drop_index", name, ())),
        drop_table=lambda name: operations.append(("drop_table", name, ())),
    )
    migration["upgrade"].__globals__["op"] = fake_op
    migration["downgrade"].__globals__["op"] = fake_op

    migration["upgrade"]()

    table_items = next(
        items
        for operation, name, items in operations
        if operation == "create_table" and name == "password_reset_tokens"
    )
    columns = {getattr(item, "name", None): item for item in table_items}
    assert {"id", "token_hash", "user_id", "expires_at", "used_at", "created_at"} <= columns.keys()
    assert {"token", "email", "password"}.isdisjoint(columns)
    token_hash_unique = getattr(columns["token_hash"], "unique", False)
    unique_constraint_names = {
        getattr(item, "name", None)
        for item in table_items
        if type(item).__name__ == "UniqueConstraint"
    }
    assert token_hash_unique or "uq_password_reset_tokens_token_hash" in unique_constraint_names
    index_names = {
        name for operation, name, _items in operations if operation == "create_index"
    }
    assert {
        "ix_password_reset_tokens_user_id",
        "ix_password_reset_tokens_expires_at",
    } <= index_names

    migration["downgrade"]()

    assert operations[-1][:2] == ("drop_table", "password_reset_tokens")
