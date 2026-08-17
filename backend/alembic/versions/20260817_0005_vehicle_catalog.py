"""Add mirrored vehicle specification catalog."""

from alembic import op
import sqlalchemy as sa

revision = "20260817_0005"
down_revision = "20260817_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_catalog_specs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("brand", sa.String(80), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("version", sa.String(180), nullable=False),
        sa.Column("powertrain", sa.String(180), nullable=False),
        sa.Column("model_year", sa.String(20), nullable=False),
        sa.Column("fuel_type", sa.String(60), nullable=False),
        sa.Column("gasoline_consumption_km_l", sa.Numeric(10, 3), nullable=True),
        sa.Column("ethanol_consumption_km_l", sa.Numeric(10, 3), nullable=True),
        sa.Column("tank_capacity_l", sa.Numeric(10, 2), nullable=True),
        sa.Column("estimated_tank_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("oil_change_km", sa.Integer(), nullable=True),
        sa.Column("oil_change_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("tire_change_km", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("brand", "model", "version", name="uq_catalog_vehicle_identity"),
    )
    op.create_index(
        "ix_catalog_category_brand",
        "vehicle_catalog_specs",
        ["category", "brand"],
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_category_brand", table_name="vehicle_catalog_specs")
    op.drop_table("vehicle_catalog_specs")
