"""Initial operational schema."""

from alembic import op
import sqlalchemy as sa

revision = "20260817_0001"
down_revision = None
branch_labels = None
depends_on = None

DEFAULT_ORGANIZATION_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="America/Sao_Paulo"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("energy_type", sa.String(32), nullable=False),
        sa.Column("odometer_km", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tank_capacity", sa.Numeric(10, 2), nullable=True),
        sa.Column("average_consumption", sa.Numeric(10, 3), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("odometer_km >= 0", name="ck_vehicles_odometer_nonnegative"),
    )
    op.create_index("ix_vehicles_organization_id", "vehicles", ["organization_id"])
    op.create_table(
        "operational_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("operation_date", sa.Date(), nullable=False),
        sa.Column("odometer_start_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("odometer_end_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("distance_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("gross_revenue", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("fuel_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("odometer_end_km >= odometer_start_km", name="ck_records_odometer_order"),
        sa.CheckConstraint("distance_km >= 0", name="ck_records_distance_nonnegative"),
        sa.CheckConstraint("gross_revenue >= 0", name="ck_records_revenue_nonnegative"),
        sa.CheckConstraint("fuel_cost >= 0", name="ck_records_fuel_cost_nonnegative"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_records_org_idempotency"),
    )
    op.create_index("ix_records_vehicle_date", "operational_records", ["vehicle_id", "operation_date"])
    op.execute(
        "INSERT INTO organizations (id, name) "
        f"VALUES ('{DEFAULT_ORGANIZATION_ID}', 'Organização Inicial')"
    )


def downgrade() -> None:
    op.drop_index("ix_records_vehicle_date", table_name="operational_records")
    op.drop_table("operational_records")
    op.drop_index("ix_vehicles_organization_id", table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_table("organizations")
