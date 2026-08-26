import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160))
    timezone: Mapped[str] = mapped_column(String(64), default="America/Sao_Paulo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("email", name="uq_users_email"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    password_hash: Mapped[str] = mapped_column(String(255))
    google_subject: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="operator")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OAuthExchangeCode(Base):
    """Código OAuth efêmero; somente o hash é persistido."""

    __tablename__ = "oauth_exchange_codes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuthLoginThrottle(Base):
    """Contador persistente de falhas sem armazenar e-mail ou endereço de origem."""

    __tablename__ = "auth_login_throttles"
    __table_args__ = (
        UniqueConstraint("scope", "key_hash", name="uq_auth_login_throttles_scope_key"),
        Index("ix_auth_login_throttles_blocked_until", "blocked_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scope: Mapped[str] = mapped_column(String(20))
    key_hash: Mapped[str] = mapped_column(String(64))
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    window_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Vehicle(Base):
    __tablename__ = "vehicles"
    __table_args__ = (CheckConstraint("odometer_km >= 0", name="ck_vehicles_odometer_nonnegative"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    catalog_spec_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicle_catalog_specs.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    plate: Mapped[str | None] = mapped_column(String(12), nullable=True)
    category: Mapped[str] = mapped_column(String(32))
    energy_type: Mapped[str] = mapped_column(String(32))
    odometer_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    tank_capacity: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    average_consumption: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    records: Mapped[list["OperationalRecord"]] = relationship(back_populates="vehicle")


class OperationalRecord(Base):
    __tablename__ = "operational_records"
    __table_args__ = (
        CheckConstraint("odometer_end_km >= odometer_start_km", name="ck_records_odometer_order"),
        CheckConstraint("distance_km >= 0", name="ck_records_distance_nonnegative"),
        CheckConstraint("gross_revenue >= 0", name="ck_records_revenue_nonnegative"),
        CheckConstraint("fuel_cost >= 0", name="ck_records_fuel_cost_nonnegative"),
        CheckConstraint("maintenance_cost >= 0", name="ck_records_maintenance_cost_nonnegative"),
        UniqueConstraint("organization_id", "idempotency_key", name="uq_records_org_idempotency"),
        Index("ix_records_vehicle_date", "vehicle_id", "operation_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id", ondelete="RESTRICT"))
    operation_date: Mapped[date] = mapped_column(Date)
    odometer_start_km: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    odometer_end_km: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    distance_km: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    gross_revenue: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    fuel_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    fuel_cost_source: Mapped[str] = mapped_column(String(20), default="informed")
    fuel_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    maintenance_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    net_profit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    vehicle: Mapped[Vehicle] = relationship(back_populates="records")


class VehicleCatalogSpec(Base):
    __tablename__ = "vehicle_catalog_specs"
    __table_args__ = (
        UniqueConstraint("brand", "model", "version", name="uq_catalog_vehicle_identity"),
        Index("ix_catalog_category_brand", "category", "brand"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    category: Mapped[str] = mapped_column(String(32))
    brand: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(120))
    version: Mapped[str] = mapped_column(String(180))
    powertrain: Mapped[str] = mapped_column(String(180))
    model_year: Mapped[str] = mapped_column(String(20))
    fuel_type: Mapped[str] = mapped_column(String(60))
    gasoline_consumption_km_l: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    ethanol_consumption_km_l: Mapped[Decimal | None] = mapped_column(Numeric(10, 3), nullable=True)
    tank_capacity_l: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    estimated_tank_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    oil_change_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oil_change_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    tire_change_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_expenses_amount_positive"),
        Index("ix_expenses_vehicle_date", "vehicle_id", "expense_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        index=True,
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expense_date: Mapped[date] = mapped_column(Date)
    category: Mapped[str] = mapped_column(String(40))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    description: Mapped[str | None] = mapped_column(String(240), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FuelPrice(Base):
    __tablename__ = "fuel_prices"
    __table_args__ = (
        CheckConstraint("unit_price > 0", name="ck_fuel_prices_unit_price_positive"),
        Index("ix_fuel_prices_lookup", "organization_id", "locality", "energy_type", "effective_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), index=True
    )
    locality: Mapped[str] = mapped_column(String(160))
    energy_type: Mapped[str] = mapped_column(String(32))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    effective_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(120))
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IntegrationReceipt(Base):
    __tablename__ = "integration_receipts"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_integration_receipts_org_key"),
        Index("ix_integration_receipts_org_created", "organization_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id", ondelete="RESTRICT"))
    idempotency_key: Mapped[str] = mapped_column(String(120))
    source: Mapped[str] = mapped_column(String(120))
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[uuid.UUID]
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceRule(Base):
    __tablename__ = "maintenance_rules"
    __table_args__ = (
        CheckConstraint(
            "interval_km IS NOT NULL OR interval_days IS NOT NULL",
            name="ck_maintenance_rules_interval_required",
        ),
        CheckConstraint("estimated_cost >= 0", name="ck_maintenance_rules_cost_nonnegative"),
        Index("ix_maintenance_rules_vehicle", "vehicle_id", "active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    name: Mapped[str] = mapped_column(String(120))
    interval_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    warning_km: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("500"))
    warning_days: Mapped[int] = mapped_column(Integer, default=15)
    baseline_odometer_km: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    baseline_date: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceExecution(Base):
    __tablename__ = "maintenance_executions"
    __table_args__ = (
        CheckConstraint("odometer_km >= 0", name="ck_maintenance_execution_odometer"),
        CheckConstraint("actual_cost >= 0", name="ck_maintenance_execution_cost"),
        Index("ix_maintenance_executions_rule_date", "rule_id", "performed_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("maintenance_rules.id"))
    performed_at: Mapped[date] = mapped_column(Date)
    odometer_km: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    actual_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    supplier: Mapped[str | None] = mapped_column(String(160), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaintenanceAlert(Base):
    __tablename__ = "maintenance_alerts"
    __table_args__ = (Index("ix_maintenance_alerts_status", "organization_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    vehicle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vehicles.id"))
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("maintenance_rules.id"))
    severity: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="open")
    due_odometer_km: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    message: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_status_created", "status", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    event_type: Mapped[str] = mapped_column(String(80))
    aggregate_type: Mapped[str] = mapped_column(String(60))
    aggregate_id: Mapped[uuid.UUID]
    payload: Mapped[dict[str, object]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
