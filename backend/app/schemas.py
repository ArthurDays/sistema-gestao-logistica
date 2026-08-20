import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

VehicleCategory = Literal["motorcycle", "car", "truck", "bus", "bicycle", "other"]
EnergyType = Literal["gasoline", "ethanol", "diesel", "cng", "electric", "hybrid", "human", "other"]
ExpenseCategory = Literal[
    "maintenance_preventive",
    "maintenance_corrective",
    "tires",
    "oil",
    "parts",
    "toll",
    "insurance",
    "taxes",
    "washing",
    "financing",
    "other",
]


class TokenCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class TokenRead(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["operator", "manager", "admin"]


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    role: str
    active: bool

    model_config = ConfigDict(from_attributes=True)


class VehicleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    category: VehicleCategory
    energy_type: EnergyType
    odometer_km: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)
    tank_capacity: Decimal | None = Field(default=None, gt=0)
    average_consumption: Decimal | None = Field(default=None, gt=0)
    plate: str | None = Field(default=None, min_length=2, max_length=12)


class VehicleRead(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    catalog_spec_id: uuid.UUID | None
    status: str
    created_at: datetime


class VehicleCatalogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category: str
    brand: str
    model: str
    version: str
    powertrain: str
    model_year: str
    fuel_type: str
    gasoline_consumption_km_l: Decimal | None
    ethanol_consumption_km_l: Decimal | None
    tank_capacity_l: Decimal | None
    estimated_tank_cost: Decimal | None
    oil_change_km: int | None
    oil_change_cost: Decimal | None
    tire_change_km: int | None
    synced_at: datetime


class CatalogSyncRead(BaseModel):
    imported: int
    updated: int
    total: int


class VehicleFromCatalogCreate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    plate: str | None = Field(default=None, min_length=2, max_length=12)
    odometer_km: Decimal = Field(default=Decimal("0"), ge=0, max_digits=12, decimal_places=2)


class OperationCreate(BaseModel):
    operation_date: date
    odometer_end_km: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    gross_revenue: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    fuel_cost: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    notes: str | None = Field(default=None, max_length=1000)


class OperationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    operation_date: date
    odometer_start_km: Decimal
    odometer_end_km: Decimal
    distance_km: Decimal
    gross_revenue: Decimal
    fuel_cost: Decimal
    fuel_cost_source: str
    fuel_unit_price: Decimal | None
    maintenance_cost: Decimal
    net_profit: Decimal
    notes: str | None
    created_at: datetime


class ExpenseCreate(BaseModel):
    vehicle_id: uuid.UUID | None = None
    expense_date: date
    category: ExpenseCategory
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    description: str | None = Field(default=None, max_length=240)


class ExpenseRead(ExpenseCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


class ProfitabilityRead(BaseModel):
    vehicle_id: uuid.UUID
    date_from: date
    date_to: date
    distance_km: Decimal
    gross_revenue: Decimal
    fuel_cost: Decimal
    other_expenses: Decimal
    maintenance_reserve: Decimal
    total_cost: Decimal
    net_profit: Decimal
    cost_per_km: Decimal
    revenue_per_km: Decimal
    net_margin_percent: Decimal


class MonthlyDashboardRead(BaseModel):
    date_from: date
    date_to: date
    gross_revenue: Decimal
    fuel_cost: Decimal
    maintenance_cost: Decimal
    net_profit: Decimal


class ExpensePeriodRead(BaseModel):
    period: str
    date_from: date
    date_to: date
    fuel_cost: Decimal
    maintenance_cost: Decimal
    other_expenses: Decimal
    total_cost: Decimal
    fuel_percent: Decimal
    maintenance_percent: Decimal
    other_percent: Decimal


class ExpenseSamplingRead(BaseModel):
    periods: list[ExpensePeriodRead]


class MaintenanceRuleCreate(BaseModel):
    vehicle_id: uuid.UUID
    name: str = Field(min_length=2, max_length=120)
    interval_km: Decimal | None = Field(default=None, gt=0)
    interval_days: int | None = Field(default=None, gt=0)
    estimated_cost: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    warning_km: Decimal = Field(default=Decimal("500"), ge=0)
    warning_days: int = Field(default=15, ge=0)


class MaintenanceRuleRead(MaintenanceRuleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    baseline_odometer_km: Decimal
    baseline_date: date
    active: bool
    created_at: datetime


class MaintenanceExecutionCreate(BaseModel):
    performed_at: date
    odometer_km: Decimal = Field(ge=0)
    actual_cost: Decimal = Field(default=Decimal("0"), ge=0)
    supplier: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)


class MaintenanceExecutionRead(MaintenanceExecutionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    rule_id: uuid.UUID
    created_at: datetime


class MaintenanceAlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    vehicle_id: uuid.UUID
    rule_id: uuid.UUID
    severity: str
    status: str
    due_odometer_km: Decimal | None
    due_date: date | None
    message: str
    created_at: datetime
    updated_at: datetime
