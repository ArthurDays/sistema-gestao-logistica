"""Persist hashed OAuth exchange and login throttling state."""

import sqlalchemy as sa

from alembic import op

revision = "20260825_0011"
down_revision = "20260821_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "oauth_exchange_codes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code_hash", name="uq_oauth_exchange_codes_code_hash"),
    )
    op.create_index(
        "ix_oauth_exchange_codes_code_hash", "oauth_exchange_codes", ["code_hash"]
    )
    op.create_index("ix_oauth_exchange_codes_user_id", "oauth_exchange_codes", ["user_id"])
    op.create_index(
        "ix_oauth_exchange_codes_expires_at", "oauth_exchange_codes", ["expires_at"]
    )

    op.create_table(
        "auth_login_throttles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("key_hash", sa.String(64), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "key_hash", name="uq_auth_login_throttles_scope_key"),
    )
    op.create_index(
        "ix_auth_login_throttles_blocked_until", "auth_login_throttles", ["blocked_until"]
    )


def downgrade() -> None:
    op.drop_index("ix_auth_login_throttles_blocked_until", table_name="auth_login_throttles")
    op.drop_table("auth_login_throttles")
    op.drop_index("ix_oauth_exchange_codes_expires_at", table_name="oauth_exchange_codes")
    op.drop_index("ix_oauth_exchange_codes_user_id", table_name="oauth_exchange_codes")
    op.drop_index("ix_oauth_exchange_codes_code_hash", table_name="oauth_exchange_codes")
    op.drop_table("oauth_exchange_codes")
