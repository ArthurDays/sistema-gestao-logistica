"""Add auditable integration receipts and fuel prices."""

from alembic import op
import sqlalchemy as sa

revision = "20260821_0008"
down_revision = "20260818_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fuel_prices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("locality", sa.String(160), nullable=False),
        sa.Column("energy_type", sa.String(32), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 3), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("unit_price > 0", name="ck_fuel_prices_unit_price_positive"),
    )
    op.create_index("ix_fuel_prices_organization_id", "fuel_prices", ["organization_id"])
    op.create_index("ix_fuel_prices_lookup", "fuel_prices", ["organization_id", "locality", "energy_type", "effective_date"])
    op.create_table(
        "integration_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
        sa.Column("resource_type", sa.String(60), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_integration_receipts_org_key"),
    )
    op.create_index("ix_integration_receipts_org_created", "integration_receipts", ["organization_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_integration_receipts_org_created", table_name="integration_receipts")
    op.drop_table("integration_receipts")
    op.drop_index("ix_fuel_prices_lookup", table_name="fuel_prices")
    op.drop_index("ix_fuel_prices_organization_id", table_name="fuel_prices")
    op.drop_table("fuel_prices")
