"""Add categorized operational expenses."""

from alembic import op
import sqlalchemy as sa

revision = "20260817_0002"
down_revision = "20260817_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "expenses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            sa.Uuid(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("description", sa.String(240), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
    )
    op.create_index("ix_expenses_vehicle_date", "expenses", ["vehicle_id", "expense_date"])
    op.create_index("ix_expenses_organization_id", "expenses", ["organization_id"])


def downgrade() -> None:
    op.drop_index("ix_expenses_organization_id", table_name="expenses")
    op.drop_index("ix_expenses_vehicle_date", table_name="expenses")
    op.drop_table("expenses")

