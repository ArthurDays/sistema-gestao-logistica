"""Link fleet vehicles to catalog specifications."""

from alembic import op
import sqlalchemy as sa

revision = "20260817_0006"
down_revision = "20260817_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "vehicles",
        sa.Column(
            "catalog_spec_id",
            sa.Uuid(),
            sa.ForeignKey("vehicle_catalog_specs.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("vehicles", sa.Column("plate", sa.String(12), nullable=True))
    op.create_index("ix_vehicles_catalog_spec_id", "vehicles", ["catalog_spec_id"])


def downgrade() -> None:
    op.drop_index("ix_vehicles_catalog_spec_id", table_name="vehicles")
    op.drop_column("vehicles", "plate")
    op.drop_column("vehicles", "catalog_spec_id")
