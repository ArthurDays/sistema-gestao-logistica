"""Add maintenance rules, executions, alerts and outbox."""

from alembic import op
import sqlalchemy as sa

revision = "20260817_0003"
down_revision = "20260817_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_rules",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("interval_km", sa.Numeric(12, 2), nullable=True),
        sa.Column("interval_days", sa.Integer(), nullable=True),
        sa.Column("estimated_cost", sa.Numeric(14, 2), nullable=False),
        sa.Column("warning_km", sa.Numeric(12, 2), nullable=False, server_default="500"),
        sa.Column("warning_days", sa.Integer(), nullable=False, server_default="15"),
        sa.Column("baseline_odometer_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("baseline_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "interval_km IS NOT NULL OR interval_days IS NOT NULL",
            name="ck_maintenance_rules_interval_required",
        ),
        sa.CheckConstraint("estimated_cost >= 0", name="ck_maintenance_rules_cost_nonnegative"),
    )
    op.create_index("ix_maintenance_rules_vehicle", "maintenance_rules", ["vehicle_id", "active"])

    op.create_table(
        "maintenance_executions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("maintenance_rules.id"), nullable=False),
        sa.Column("performed_at", sa.Date(), nullable=False),
        sa.Column("odometer_km", sa.Numeric(12, 2), nullable=False),
        sa.Column("actual_cost", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("supplier", sa.String(160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("odometer_km >= 0", name="ck_maintenance_execution_odometer"),
        sa.CheckConstraint("actual_cost >= 0", name="ck_maintenance_execution_cost"),
    )
    op.create_index(
        "ix_maintenance_executions_rule_date",
        "maintenance_executions",
        ["rule_id", "performed_at"],
    )

    op.create_table(
        "maintenance_alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("rule_id", sa.Uuid(), sa.ForeignKey("maintenance_rules.id"), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("due_odometer_km", sa.Numeric(12, 2), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("message", sa.String(300), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_maintenance_alerts_status", "maintenance_alerts", ["organization_id", "status"])

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("aggregate_type", sa.String(60), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_outbox_status_created", "outbox_events", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_outbox_status_created", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index("ix_maintenance_alerts_status", table_name="maintenance_alerts")
    op.drop_table("maintenance_alerts")
    op.drop_index("ix_maintenance_executions_rule_date", table_name="maintenance_executions")
    op.drop_table("maintenance_executions")
    op.drop_index("ix_maintenance_rules_vehicle", table_name="maintenance_rules")
    op.drop_table("maintenance_rules")

