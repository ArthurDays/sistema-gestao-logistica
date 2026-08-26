import hashlib
import hmac
import secrets
import uuid
from calendar import monthrange
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import (
    AuthenticationThrottled,
    CurrentUser,
    authenticate_with_throttle,
    current_organization_id,
    get_current_user,
    require_roles,
)
from app.catalog import sync_catalog
from app.core.config import settings
from app.core.security import create_access_token, create_oauth_state, hash_password, verify_oauth_state
from app.db import get_db
from app.maintenance import evaluate_maintenance, maintenance_reserve_per_km
from app.models import (
    Expense,
    FuelPrice,
    IntegrationReceipt,
    MaintenanceAlert,
    MaintenanceExecution,
    MaintenanceRule,
    OAuthExchangeCode,
    OperationalRecord,
    Organization,
    User,
    Vehicle,
    VehicleCatalogSpec,
)
from app.schemas import (
    CatalogSyncRead,
    ExpenseCreate,
    ExpensePeriodRead,
    ExpenseRead,
    ExpenseSamplingRead,
    FuelPriceIntegrationCreate,
    IntegrationReceiptRead,
    IntegrationVehicleDataCreate,
    MaintenanceAlertRead,
    MaintenanceExecutionCreate,
    MaintenanceExecutionRead,
    MaintenanceRuleCreate,
    MaintenanceRuleRead,
    MonthlyDashboardRead,
    OAuthExchangeCreate,
    OperationCreate,
    OperationRead,
    OrganizationRegister,
    ProfitabilityRead,
    SessionRead,
    TokenCreate,
    TokenRead,
    UserCreate,
    UserRead,
    VehicleCatalogRead,
    VehicleCreate,
    VehicleFromCatalogCreate,
    VehicleRead,
)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
router = APIRouter(prefix="/api/v1", dependencies=[Depends(get_current_user)])
DbSession = Annotated[Session, Depends(get_db)]
IdempotencyKey = Annotated[
    str,
    Header(min_length=8, max_length=120, alias="Idempotency-Key"),
]


@auth_router.post("/token", response_model=TokenRead)
def create_token(request: Request, payload: TokenCreate, db: DbSession) -> TokenRead:
    source = request.client.host if request.client is not None else "unknown"
    try:
        user = authenticate_with_throttle(payload.email, payload.password, source, db)
    except AuthenticationThrottled as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Muitas tentativas de autenticação. Tente novamente mais tarde.",
            headers={"Retry-After": str(error.retry_after)},
        ) from error
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    return TokenRead(access_token=create_access_token(str(user.id), str(user.organization_id), user.role))


@auth_router.get("/google")
def start_google_oauth() -> RedirectResponse:
    oauth_settings = (
        settings.google_oauth_client_id,
        settings.google_oauth_client_secret,
        settings.google_oauth_redirect_uri,
    )
    if not all(oauth_settings):
        raise HTTPException(status_code=503, detail="Google OAuth não configurado")
    state = create_oauth_state()
    params = {
        "client_id": settings.google_oauth_client_id,
        "redirect_uri": settings.google_oauth_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    response = RedirectResponse(
        "https://accounts.google.com/o/oauth2/v2/auth?" + str(httpx.QueryParams(params))
    )
    response.set_cookie(
        "oauth_correlation",
        state,
        max_age=600,
        httponly=True,
        secure=settings.oauth_cookie_secure,
        samesite="lax",
        path="/api/v1/auth/google",
    )
    return response


@auth_router.get("/google/callback")
async def finish_google_oauth(
    code: str,
    state: str,
    db: DbSession,
    oauth_correlation: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    if oauth_correlation is None or not hmac.compare_digest(oauth_correlation, state):
        raise HTTPException(status_code=401, detail="Estado OAuth inválido")
    verify_oauth_state(state)
    oauth_settings = (
        settings.google_oauth_client_id,
        settings.google_oauth_client_secret,
        settings.google_oauth_redirect_uri,
    )
    if not all(oauth_settings):
        raise HTTPException(status_code=503, detail="Google OAuth não configurado")
    async with httpx.AsyncClient(timeout=10) as client:
        token = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "redirect_uri": settings.google_oauth_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        token.raise_for_status()
        profile = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token.json()['access_token']}"},
        )
        profile.raise_for_status()
    identity = profile.json()
    valid_identity = (
        identity.get("email_verified")
        and isinstance(identity.get("sub"), str)
        and isinstance(identity.get("email"), str)
    )
    if not valid_identity:
        raise HTTPException(status_code=401, detail="Identidade Google inválida")
    user = db.scalar(select(User).where(User.email == identity["email"].casefold(), User.active.is_(True)))
    if user is None or (user.google_subject is not None and user.google_subject != identity["sub"]):
        raise HTTPException(
            status_code=403,
            detail="Conta Google não autorizada; crie sua organização primeiro",
        )
    user.google_subject = identity["sub"]
    raw_exchange_code = secrets.token_urlsafe(32)
    db.add(
        OAuthExchangeCode(
            code_hash=hashlib.sha256(raw_exchange_code.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(UTC) + timedelta(minutes=2),
        )
    )
    db.commit()
    frontend_url = settings.frontend_url.rstrip("/")
    response = RedirectResponse(
        f"{frontend_url}/?" + str(httpx.QueryParams({"auth_code": raw_exchange_code}))
    )
    response.delete_cookie(
        "oauth_correlation",
        path="/api/v1/auth/google",
        secure=settings.oauth_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@auth_router.post("/exchange", response_model=TokenRead)
def exchange_oauth_code(payload: OAuthExchangeCreate, db: DbSession) -> TokenRead:
    now = datetime.now(UTC)
    db.execute(
        delete(OAuthExchangeCode)
        .where(OAuthExchangeCode.expires_at < now - timedelta(days=1))
        .execution_options(synchronize_session=False)
    )
    db.commit()
    code_hash = hashlib.sha256(payload.code.encode()).hexdigest()
    exchange_code = db.scalar(
        select(OAuthExchangeCode)
        .where(OAuthExchangeCode.code_hash == code_hash, OAuthExchangeCode.used_at.is_(None))
        .with_for_update()
    )
    if exchange_code is None:
        raise HTTPException(status_code=401, detail="Código de autenticação inválido ou expirado")
    expires_at = exchange_code.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at <= now:
        raise HTTPException(status_code=401, detail="Código de autenticação inválido ou expirado")
    user = db.get(User, exchange_code.user_id)
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Código de autenticação inválido ou expirado")
    exchange_code.used_at = now
    db.commit()
    return TokenRead(access_token=create_access_token(str(user.id), str(user.organization_id), user.role))


@auth_router.post("/register", response_model=TokenRead, status_code=status.HTTP_201_CREATED)
def register_organization(payload: OrganizationRegister, db: DbSession) -> TokenRead:
    organization = Organization(name=payload.organization_name)
    db.add(organization)
    db.flush()
    user = User(
        organization_id=organization.id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role="admin",
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado") from error
    return TokenRead(access_token=create_access_token(str(user.id), str(organization.id), user.role))


@auth_router.get("/me", response_model=SessionRead)
def read_session(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: DbSession,
) -> SessionRead:
    user = db.get(User, current_user.id)
    organization = db.get(Organization, current_user.organization_id)
    if user is None or organization is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão inválida")
    return SessionRead(
        user_id=user.id,
        organization_id=organization.id,
        organization_name=organization.name,
        email=user.email,
        role=user.role,
    )


@auth_router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbSession,
    _admin: Annotated[object, Depends(require_roles("admin"))],
) -> User:
    user = User(
        organization_id=current_organization_id(),
        email=payload.email.casefold(),
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail já cadastrado") from error
    db.refresh(user)
    return user


@router.get("/vehicles", response_model=list[VehicleRead])
def list_vehicles(db: DbSession) -> list[Vehicle]:
    return list(
        db.scalars(
            select(Vehicle)
            .where(Vehicle.organization_id == current_organization_id())
            .order_by(Vehicle.name)
        )
    )


@router.post(
    "/vehicles", response_model=VehicleRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin"))],
)
def create_vehicle(payload: VehicleCreate, db: DbSession) -> Vehicle:
    vehicle = Vehicle(organization_id=current_organization_id(), **payload.model_dump())
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


@router.post(
    "/vehicle-catalog/sync",
    response_model=CatalogSyncRead,
    dependencies=[Depends(require_roles("admin"))],
)
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
    dependencies=[Depends(require_roles("admin"))],
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
    category_map = {"Carro": "car", "Moto": "motorcycle", "Caminhão": "truck", "Ônibus": "bus"}
    fuel_description = spec.fuel_type.casefold()
    if "elétrico" in fuel_description or "eletrico" in fuel_description:
        energy_type = "electric"
    elif "híbrido" in fuel_description or "hibrido" in fuel_description:
        energy_type = "hybrid"
    elif "diesel" in fuel_description:
        energy_type = "diesel"
    elif "gnv" in fuel_description:
        energy_type = "cng"
    elif (
        "álcool" in fuel_description or "etanol" in fuel_description
    ) and "gasolina" not in fuel_description:
        energy_type = "ethanol"
    else:
        energy_type = "gasoline"

    vehicle = Vehicle(
        organization_id=current_organization_id(),
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
    if spec.oil_change_km and spec.oil_change_cost and spec.oil_change_cost > 0:
        db.add(
            MaintenanceRule(
                organization_id=current_organization_id(),
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
                organization_id=current_organization_id(),
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
    dependencies=[Depends(require_roles("operator", "manager", "admin"))],
)
def create_operation(
    vehicle_id: uuid.UUID,
    payload: OperationCreate,
    db: DbSession,
    idempotency_key: IdempotencyKey,
) -> OperationalRecord:
    existing = db.scalar(
        select(OperationalRecord).where(
            OperationalRecord.organization_id == current_organization_id(),
            OperationalRecord.idempotency_key == idempotency_key,
        )
    )
    if existing:
        return existing

    vehicle = db.scalar(
        select(Vehicle)
        .where(
            Vehicle.id == vehicle_id,
            Vehicle.organization_id == current_organization_id(),
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
        organization_id=current_organization_id(),
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


@router.post(
    "/expenses", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("manager", "admin"))],
)
def create_expense(payload: ExpenseCreate, db: DbSession) -> Expense:
    if payload.vehicle_id is not None:
        vehicle_exists = db.scalar(
            select(Vehicle.id).where(
                Vehicle.id == payload.vehicle_id,
                Vehicle.organization_id == current_organization_id(),
            )
        )
        if vehicle_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    expense = Expense(organization_id=current_organization_id(), **payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


@router.post(
    "/integrations/vehicle-data",
    response_model=IntegrationReceiptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin"))],
)
def import_vehicle_data(
    payload: IntegrationVehicleDataCreate,
    db: DbSession,
    idempotency_key: IdempotencyKey,
) -> IntegrationReceipt:
    organization_id = current_organization_id()
    existing = db.scalar(
        select(IntegrationReceipt).where(
            IntegrationReceipt.organization_id == organization_id,
            IntegrationReceipt.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing

    vehicle = db.scalar(
        select(Vehicle).where(Vehicle.id == payload.vehicle_id, Vehicle.organization_id == organization_id)
    )
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")
    changes = payload.model_dump(exclude={"source", "vehicle_id"}, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Informe dados técnicos")
    for field, value in changes.items():
        setattr(vehicle, field, value)
    receipt = IntegrationReceipt(
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        source=payload.source,
        resource_type="vehicle",
        resource_id=vehicle.id,
        payload=payload.model_dump(mode="json"),
    )
    db.add(receipt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        concurrent_receipt = db.scalar(
            select(IntegrationReceipt).where(
                IntegrationReceipt.organization_id == organization_id,
                IntegrationReceipt.idempotency_key == idempotency_key,
            )
        )
        if concurrent_receipt is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não foi possível registrar a integração",
            ) from None
        return concurrent_receipt
    db.refresh(receipt)
    return receipt


@router.post(
    "/integrations/fuel-prices",
    response_model=IntegrationReceiptRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("admin"))],
)
def import_fuel_price(
    payload: FuelPriceIntegrationCreate,
    db: DbSession,
    idempotency_key: IdempotencyKey,
) -> IntegrationReceipt:
    organization_id = current_organization_id()
    existing = db.scalar(
        select(IntegrationReceipt).where(
            IntegrationReceipt.organization_id == organization_id,
            IntegrationReceipt.idempotency_key == idempotency_key,
        )
    )
    if existing is not None:
        return existing
    fuel_price = FuelPrice(
        organization_id=organization_id,
        locality=payload.locality.strip(),
        energy_type=payload.energy_type,
        unit_price=payload.unit_price,
        effective_date=payload.effective_date,
        source=payload.source,
    )
    db.add(fuel_price)
    db.flush()
    receipt = IntegrationReceipt(
        organization_id=organization_id,
        idempotency_key=idempotency_key,
        source=payload.source,
        resource_type="fuel_price",
        resource_id=fuel_price.id,
        payload=payload.model_dump(mode="json"),
    )
    db.add(receipt)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        concurrent_receipt = db.scalar(
            select(IntegrationReceipt).where(
                IntegrationReceipt.organization_id == organization_id,
                IntegrationReceipt.idempotency_key == idempotency_key,
            )
        )
        if concurrent_receipt is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não foi possível registrar a integração",
            ) from None
        return concurrent_receipt
    db.refresh(receipt)
    return receipt


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
            Vehicle.organization_id == current_organization_id(),
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
            OperationalRecord.organization_id == current_organization_id(),
            OperationalRecord.vehicle_id == vehicle_id,
            OperationalRecord.operation_date.between(date_from, date_to),
        )
    ).one()
    other_expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.organization_id == current_organization_id(),
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
            OperationalRecord.organization_id == current_organization_id(),
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
            OperationalRecord.organization_id == current_organization_id(),
            OperationalRecord.operation_date.between(date_from, date_to),
        )
    ).one()
    other_expenses = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(
            Expense.organization_id == current_organization_id(),
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
        MaintenanceRule.organization_id == current_organization_id(),
        MaintenanceRule.active.is_(True),
    )
    if vehicle_id is not None:
        query = query.where(MaintenanceRule.vehicle_id == vehicle_id)
    return list(db.scalars(query.order_by(MaintenanceRule.name)))


@router.post(
    "/maintenance-rules",
    response_model=MaintenanceRuleRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("manager", "admin"))],
)
def create_maintenance_rule(payload: MaintenanceRuleCreate, db: DbSession) -> MaintenanceRule:
    if payload.interval_km is None and payload.interval_days is None:
        raise HTTPException(status_code=422, detail="Informe intervalo em KM, dias ou ambos")
    vehicle = db.scalar(
        select(Vehicle).where(
            Vehicle.id == payload.vehicle_id,
            Vehicle.organization_id == current_organization_id(),
        )
    )
    if vehicle is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Veículo não encontrado")

    rule = MaintenanceRule(
        organization_id=current_organization_id(),
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
    dependencies=[Depends(require_roles("manager", "admin"))],
)
def create_maintenance_execution(
    rule_id: uuid.UUID,
    payload: MaintenanceExecutionCreate,
    db: DbSession,
) -> MaintenanceExecution:
    rule = db.scalar(
        select(MaintenanceRule).where(
            MaintenanceRule.id == rule_id,
            MaintenanceRule.organization_id == current_organization_id(),
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
        organization_id=current_organization_id(),
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
            Vehicle.organization_id == current_organization_id(),
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
                MaintenanceAlert.organization_id == current_organization_id(),
                MaintenanceAlert.status == status_filter,
            )
            .order_by(MaintenanceAlert.created_at.desc())
        )
    )
