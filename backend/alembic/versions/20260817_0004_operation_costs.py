"""Freeze calculated fuel, maintenance and net profit per operation."""

from alembic import op
import sqlalchemy as sa

revision = "20260817_0004"
down_revision = "20260817_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "operational_records",
        sa.Column("fuel_cost_source", sa.String(20), nullable=False, server_default="informed"),
    )
    op.add_column(
        "operational_records",
        sa.Column("fuel_unit_price", sa.Numeric(10, 3), nullable=True),
    )
    op.add_column(
        "operational_records",
        sa.Column("maintenance_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.add_column(
        "operational_records",
        sa.Column("net_profit", sa.Numeric(14, 2), nullable=False, server_default="0"),
    )
    op.execute(
        "UPDATE operational_records "
        "SET net_profit = gross_revenue - fuel_cost - maintenance_cost"
    )
    op.create_check_constraint(
        "ck_records_maintenance_cost_nonnegative",
        "operational_records",
        "maintenance_cost >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_records_maintenance_cost_nonnegative",
        "operational_records",
        type_="check",
    )
    op.drop_column("operational_records", "net_profit")
    op.drop_column("operational_records", "maintenance_cost")
    op.drop_column("operational_records", "fuel_unit_price")
    op.drop_column("operational_records", "fuel_cost_source")
