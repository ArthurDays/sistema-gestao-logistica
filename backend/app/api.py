import uuid
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.catalog import sync_catalog
from app.core.config import settings
from app.db import get_db
from app.maintenance import evaluate_maintenance, maintenance_reserve_per_km
from app.models import (
    Expense,
    MaintenanceAlert,
    MaintenanceExecution,
    MaintenanceRule,
    OperationalRecord,
    Vehicle,
    VehicleCatalogSpec,
)
from app.schemas import (
    CatalogSyncRead,
    ExpenseCreate,
    ExpensePeriodRead,
    ExpenseRead,
    ExpenseSamplingRead,
    MaintenanceAlertRead,
    MaintenanceExecutionCreate,
    MaintenanceExecutionRead,
    MaintenanceRuleCreate,
    MaintenanceRuleRead,
    MonthlyDashboardRead,
    OperationCreate,
    OperationRead,
    ProfitabilityRead,
    VehicleCatalogRead,
    VehicleCreate,
    VehicleFromCatalogCreate,
    VehicleRead,
)

router = APIRouter(prefix="/api/v1")
DEFAULT_ORGANIZATION_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[
    str,
    Header(min_length=8, max_length=120, alias="Idempotency-Key"),
]


@router.get("/vehicles", response_model=list[VehicleRead])
def list_vehicles(db: DbSession) -> list[Vehicle]:
    return list(
        db.scalars(
            select(Vehicle)
            .where(Vehicle.organization_id == DEFAULT_ORGANIZATION_ID)
            .order_by(Vehicle.name)
        )
    )


@router.post("/vehicles", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: DbSession) -> Vehicle:
    vehicle = Vehicle(organization_id=DEFAULT_ORGANIZATION_ID, **payload.model_dump())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.get("/vehicle-catalog", response_model=list[VehicleCatalogRead])
def list_vehicle_catalog(
    db: DbSession,
    category: str | None = None,
    search: str | None = None,
) -> list[VehicleCatalogSpec]:
    query = select(VehicleCatalogSpec).where(VehicleCatalogSpec.active.is_(True))
    if category:
        query = query.where(VehicleCatalogSpec.category == category)
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                VehicleCatalogSpec.brand.ilike(term),
                VehicleCatalogSpec.model.ilike(term),
                VehicleCatalogSpec.version.ilike(term),
            )
        )
    return list(
        db.scalars(
            query.order_by(
                VehicleCatalogSpec.category,
                VehicleCatalogSpec.brand,
                VehicleCatalogSpec.model,
            )
        )
    )


@router.post("/vehicle-catalog/sync", response_model=CatalogSyncRead)
def synchronize_vehicle_catalog(db: DbSession) -> CatalogSyncRead:
    try:
        imported, updated, total = sync_catalog(db)
    except (OSError, ValueError) as error:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Falha ao sincronizar planilha: {error}") from error
    return CatalogSyncRead(imported=imported, updated=updated, total=total)


@router.post(
    "/vehicle-catalog/{spec_id}/register",
    response_model=VehicleRead,
    status_code=status.HTTP_201_CREATED,
)
def register_vehicle_from_catalog(
    spec_id: uuid.UUID,
    payload: VehicleFromCatalogCreate,
    db: DbSession,
) -> Vehicle:
    spec = db.scalar(
        select(VehicleCatalogSpec).where(
            VehicleCatalogSpec.id == spec_id,
            VehicleCatalogSpec.active.is_(True),
        )
    )
    if spec is None:
        raise HTTPException(status_code=404, detail="Modelo não encontrado no catálogo")
    category_map = {"Carro": "car", "Moto": "motorcycle"}
    fuel_description = spec.fuel_type.casefold()
    if "diesel" in fuel_description:
        energy_type = "diesel"
    elif "álcool" in fuel_description or "etanol" in fuel_description:
        energy_type = "ethanol"
    else:
        energy_type = "gasoline"

    vehicle = Vehicle(
        organization_id=DEFAULT_ORGANIZATION_ID,
        catalog_spec_id=spec.id,
        name=payload.name or f"{spec.brand} {spec.model}",
        plate=payload.plate.upper().strip() if payload.plate else None,
        category=category_map.get(spec.category, "other"),
        energy_type=energy_type,
        odometer_km=payload.odometer_km,
        tank_capacity=spec.tank_capacity_l,
        average_consumption=spec.gasoline_consumption_km_l,
    )
    db.add(vehicle)
    db.flush()
    if spec.oil_change_km:
        db.add(
            MaintenanceRule(
                organization_id=DEFAULT_ORGANIZATION_ID,
                vehicle_id=vehicle.id,
                name="Troca de óleo",
                interval_km=Decimal(spec.oil_change_km),
                estimated_cost=spec.oil_change_cost or Decimal("0"),
                baseline_odometer_km=payload.odometer_km,
                baseline_date=date.today(),
            )
        )
    if spec.tire_change_km:
        db.add(
            MaintenanceRule(
                organization_id=DEFAULT_ORGANIZATION_ID,
                vehicle_id=vehicle.id,
                name="Troca de pneus",
                interval_km=Decimal(spec.tire_change_km),
                estimated_cost=Decimal("0"),
                baseline_odometer_km=payload.odometer_km,
                baseline_date=date.today(),
            )
        )
    db.commit()
    db.refresh(vehicle)
    return vehicle


@router.post(
    "/vehicles/{vehicle_id}/operations",
    response_model=OperationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_operation(
    vehicle_id: uuid.UUID,
    payload: OperationCreate,
    db: DbSession,
    idempotency_key: IdempotencyKey,
) -> OperationalRecord:
    existing = db.scalar(
        select(OperationalRecord).where(
            OperationalRecord.organization_id == DEFAULT_ORGANIZATION_ID,
            OperationalRecord.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing

    vehicle = db.scalar(
        select(Vehicle)
        .where(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == DEFAULT_ORGANIZATION_ID,
        )
        .with_for_update()
    )
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")
    if vehicle.status != "active":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Veículo não está ativo")
    if payload.odometer_end_km < vehicle.odometer_km:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hodômetro final não pode ser menor que o hodômetro atual",
        )

    distance = payload.odometer_end_km - vehicle.odometer_km
    if payload.fuel_cost is not None and payload.fuel_cost > 0:
        fuel_cost = payload.fuel_cost
        fuel_cost_source = "informed"
        fuel_unit_price = None
    elif distance == 0:
        fuel_cost = Decimal("0.00")
        fuel_cost_source = "calculated"
        fuel_unit_price = settings.base_fuel_price_per_liter
    else:
        if vehicle.average_consumption is None or vehicle.average_consumption <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Informe o custo de combustível ou cadastre o consumo médio "
                    "do veículo para o cálculo automático"
                ),
            )
        fuel_cost = (
            distance / vehicle.average_consumption * settings.base_fuel_price_per_liter
        ).quantize(Decimal("0.01"))
        fuel_cost_source = "calculated"
        fuel_unit_price = settings.base_fuel_price_per_liter

    maintenance_cost = (
        distance * maintenance_reserve_per_km(db, vehicle.id)
    ).quantize(Decimal("0.01"))
    net_profit = payload.gross_revenue - fuel_cost - maintenance_cost
    record = OperationalRecord(
        organization_id=DEFAULT_ORGANIZATION_ID,
        vehicle_id=vehicle.id,
        operation_date=payload.operation_date,
        odometer_start_km=vehicle.odometer_km,
        odometer_end_km=payload.odometer_end_km,
        distance_km=distance,
        gross_revenue=payload.gross_revenue,
        fuel_cost=fuel_cost,
        fuel_cost_source=fuel_cost_source,
        fuel_unit_price=fuel_unit_price,
        maintenance_cost=maintenance_cost,
        net_profit=net_profit,
        notes=payload.notes,
        idempotency_key=idempotency_key,
    )
    vehicle.odometer_km = payload.odometer_end_km
    db.add(record)
    db.flush()
    evaluate_maintenance(db, vehicle, payload.operation_date)
    db.commit()
    db.refresh(record)
    return record


@router.post("/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def create_expense(payload: ExpenseCreate, db: DbSession) -> Expense:
    if payload.vehicle_id is not None:
        vehicle_exists = db.scalar(
            select(Vehicle.id).where(
                Vehicle.id == payload.vehicle_id,
                Vehicle.organization_id == DEFAULT_ORGANIZATION_ID,
            )
        )
        if vehicle_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    expense = Expense(organization_id=DEFAULT_ORGANIZATION_ID, **payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.get("/vehicles/{vehicle_id}/profitability", response_model=ProfitabilityRead)
def get_profitability(
    vehicle_id: uuid.UUID,
    date_from: date,
    date_to: date,
    db: DbSession,
) -> ProfitabilityRead:
    if date_to < date_from:
        raise HTTPException(status_code=422, detail="A data final deve ser igual ou posterior à inicial")

    vehicle_exists = db.scalar(
        select(Vehicle.id).where(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == DEFAULT_ORGANIZATION_ID,
        )
    )
    if vehicle_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    operation_totals = db.execute(
        select(
            func.coalesce(func.sum(OperationalRecord.distance_km), 0),
            func.coalesce(func.sum(OperationalRecord.gross_revenue), 0),
            func.coalesce(func.sum(OperationalRecord.fuel_cost), 0),
            func.coalesce(func.sum(OperationalRecord.maintenance_cost), 0),
        ).where(
            OperationalRecord.organization_id == DEFAULT_ORGANIZATION_ID,
            OperationalRecord.vehicle_id == vehicle_id,
            OperationalRecord.operation_date.between(date_from, date_to),
        )
    ).one()
    other_expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.organization_id == DEFAULT_ORGANIZATION_ID,
            Expense.vehicle_id == vehicle_id,
            Expense.expense_date.between(date_from, date_to),
        )
    )

    distance = Decimal(operation_totals[0])
    revenue = Decimal(operation_totals[1])
    fuel = Decimal(operation_totals[2])
    maintenance_reserve = Decimal(operation_totals[3])
    expenses = Decimal(other_expenses or 0)
    total_cost = fuel + expenses + maintenance_reserve
    net_profit = revenue - total_cost
    zero = Decimal("0.00")
    hundred = Decimal("100")

    return ProfitabilityRead(
        vehicle_id=vehicle_id,
        date_from=date_from,
        date_to=date_to,
        distance_km=distance,
        gross_revenue=revenue,
        fuel_cost=fuel,
        other_expenses=expenses,
        maintenance_reserve=maintenance_reserve,
        total_cost=total_cost,
        net_profit=net_profit,
        cost_per_km=(total_cost / distance).quantize(Decimal("0.01")) if distance else zero,
        revenue_per_km=(revenue / distance).quantize(Decimal("0.01")) if distance else zero,
        net_margin_percent=(net_profit / revenue * hundred).quantize(Decimal("0.01")) if revenue else zero,
    )


@router.get("/dashboard/monthly-summary", response_model=MonthlyDashboardRead)
def get_monthly_dashboard(db: DbSession, reference_date: date | None = None) -> MonthlyDashboardRead:
    reference = reference_date or date.today()
    date_from = reference.replace(day=1)
    date_to = reference.replace(day=monthrange(reference.year, reference.month)[1])
    totals = db.execute(
        select(
            func.coalesce(func.sum(OperationalRecord.gross_revenue), 0),
            func.coalesce(func.sum(OperationalRecord.fuel_cost), 0),
            func.coalesce(func.sum(OperationalRecord.maintenance_cost), 0),
            func.coalesce(func.sum(OperationalRecord.net_profit), 0),
        ).where(
            OperationalRecord.organization_id == DEFAULT_ORGANIZATION_ID,
            OperationalRecord.operation_date.between(date_from, date_to),
        )
    ).one()
    return MonthlyDashboardRead(
        date_from=date_from,
        date_to=date_to,
        gross_revenue=Decimal(totals[0]),
        fuel_cost=Decimal(totals[1]),
        maintenance_cost=Decimal(totals[2]),
        net_profit=Decimal(totals[3]),
    )


def _expense_period(
    db: Session,
    period: str,
    date_from: date,
    date_to: date,
) -> ExpensePeriodRead:
    operation_costs = db.execute(
        select(
            func.coalesce(func.sum(OperationalRecord.fuel_cost), 0),
            func.coalesce(func.sum(OperationalRecord.maintenance_cost), 0),
        ).where(
            OperationalRecord.organization_id == DEFAULT_ORGANIZATION_ID,
            OperationalRecord.operation_date.between(date_from, date_to),
        )
    ).one()
    other_expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.organization_id == DEFAULT_ORGANIZATION_ID,
            Expense.expense_date.between(date_from, date_to),
        )
    )
    fuel = Decimal(operation_costs[0])
    maintenance = Decimal(operation_costs[1])
    other = Decimal(other_expenses or 0)
    total = fuel + maintenance + other
    hundred = Decimal("100")
    zero = Decimal("0.00")

    def percent(value: Decimal) -> Decimal:
        return (value / total * hundred).quantize(Decimal("0.01")) if total else zero

    return ExpensePeriodRead(
        period=period,
        date_from=date_from,
        date_to=date_to,
        fuel_cost=fuel,
        maintenance_cost=maintenance,
        other_expenses=other,
        total_cost=total,
        fuel_percent=percent(fuel),
        maintenance_percent=percent(maintenance),
        other_percent=percent(other),
    )


@router.get("/dashboard/expense-sampling", response_model=ExpenseSamplingRead)
def get_expense_sampling(db: DbSession, reference_date: date | None = None) -> ExpenseSamplingRead:
    reference = reference_date or date.today()
    week_from = reference - timedelta(days=reference.weekday())
    month_from = reference.replace(day=1)
    return ExpenseSamplingRead(
        periods=[
            _expense_period(db, "day", reference, reference),
            _expense_period(db, "week", week_from, reference),
            _expense_period(db, "month", month_from, reference),
        ]
    )


@router.get("/maintenance-rules", response_model=list[MaintenanceRuleRead])
def list_maintenance_rules(db: DbSession, vehicle_id: uuid.UUID | None = None) -> list[MaintenanceRule]:
    query = select(MaintenanceRule).where(
        MaintenanceRule.organization_id == DEFAULT_ORGANIZATION_ID,
        MaintenanceRule.active.is_(True),
    )
    if vehicle_id is not None:
        query = query.where(MaintenanceRule.vehicle_id == vehicle_id)
    return list(db.scalars(query.order_by(MaintenanceRule.name)))


@router.post(
    "/maintenance-rules",
    response_model=MaintenanceRuleRead,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_rule(payload: MaintenanceRuleCreate, db: DbSession) -> MaintenanceRule:
    if payload.interval_km is None and payload.interval_days is None:
        raise HTTPException(status_code=422, detail="Informe intervalo em KM, dias ou ambos")
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == payload.vehicle_id,
            Vehicle.organization_id == DEFAULT_ORGANIZATION_ID,
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    rule = MaintenanceRule(
        organization_id=DEFAULT_ORGANIZATION_ID,
        baseline_odometer_km=vehicle.odometer_km,
        baseline_date=date.today(),
        **payload.model_dump(),
    )
    db.add(rule)
    db.flush()
    evaluate_maintenance(db, vehicle)
    db.commit()
    db.refresh(rule)
    return rule


@router.post(
    "/maintenance-rules/{rule_id}/executions",
    response_model=MaintenanceExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance_execution(
    rule_id: uuid.UUID,
    payload: MaintenanceExecutionCreate,
    db: DbSession,
) -> MaintenanceExecution:
    rule = db.scalar(
        select(MaintenanceRule).where(
            MaintenanceRule.id == rule_id,
            MaintenanceRule.organization_id == DEFAULT_ORGANIZATION_ID,
        )
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Regra não encontrada")
    vehicle = db.get(Vehicle, rule.vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")
    if payload.odometer_km > vehicle.odometer_km:
        raise HTTPException(status_code=422, detail="KM da manutenção supera o hodômetro atual")

    execution = MaintenanceExecution(
        organization_id=DEFAULT_ORGANIZATION_ID,
        vehicle_id=vehicle.id,
        rule_id=rule.id,
        **payload.model_dump(),
    )
    db.add(execution)
    db.flush()
    evaluate_maintenance(db, vehicle, payload.performed_at)
    db.commit()
    db.refresh(execution)
    return execution


@router.get("/maintenance-alerts", response_model=list[MaintenanceAlertRead])
def list_maintenance_alerts(db: DbSession, status_filter: str = "open") -> list[MaintenanceAlert]:
    vehicles = db.scalars(
        select(Vehicle).where(
            Vehicle.organization_id == DEFAULT_ORGANIZATION_ID,
            Vehicle.status == "active",
        )
    )
    for vehicle in vehicles:
        evaluate_maintenance(db, vehicle)
    db.commit()
    return list(
        db.scalars(
            select(MaintenanceAlert)
            .where(
                MaintenanceAlert.organization_id == DEFAULT_ORGANIZATION_ID,
                MaintenanceAlert.status == status_filter,
            )
            .order_by(MaintenanceAlert.created_at.desc())
        )
    )
