"""Persist immutable Google OAuth subjects."""
from alembic import op
import sqlalchemy as sa

revision = "20260821_0010"
down_revision = "20260821_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_subject", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_subject", "users", ["google_subject"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_subject", "users", type_="unique")
    op.drop_column("users", "google_subject")
