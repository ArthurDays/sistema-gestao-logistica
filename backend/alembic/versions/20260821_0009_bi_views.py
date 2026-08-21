"""Add read-only operational views for BI."""

from alembic import op

revision = "20260821_0009"
down_revision = "20260821_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW bi_vehicle_daily AS
        SELECT r.organization_id, r.vehicle_id, v.name AS vehicle_name, v.category,
               r.operation_date, r.distance_km, r.gross_revenue, r.fuel_cost,
               r.maintenance_cost, r.net_profit
        FROM operational_records r
        JOIN vehicles v ON v.id = r.vehicle_id
    """)
    op.execute("""
        CREATE VIEW bi_maintenance_alerts AS
        SELECT a.organization_id, a.id AS alert_id, a.vehicle_id, v.name AS vehicle_name,
               a.severity, a.status, a.due_odometer_km, a.due_date, a.created_at, a.resolved_at
        FROM maintenance_alerts a
        JOIN vehicles v ON v.id = a.vehicle_id
    """)
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'metabase_bi') THEN
                GRANT SELECT ON bi_vehicle_daily, bi_maintenance_alerts TO metabase_bi;
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("DROP VIEW bi_maintenance_alerts")
    op.execute("DROP VIEW bi_vehicle_daily")
