import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    MaintenanceAlert,
    MaintenanceExecution,
    MaintenanceRule,
    OutboxEvent,
    Vehicle,
)


def _latest_execution(db: Session, rule_id: uuid.UUID) -> MaintenanceExecution | None:
    return db.scalar(
        select(MaintenanceExecution)
        .where(MaintenanceExecution.rule_id == rule_id)
        .order_by(MaintenanceExecution.performed_at.desc(), MaintenanceExecution.created_at.desc())
        .limit(1)
    )


def maintenance_reserve_per_km(db: Session, vehicle_id: uuid.UUID) -> Decimal:
    rules = db.scalars(
        select(MaintenanceRule).where(
            MaintenanceRule.vehicle_id == vehicle_id,
            MaintenanceRule.active.is_(True),
            MaintenanceRule.interval_km.is_not(None),
        )
    )
    return sum(
        (rule.estimated_cost / rule.interval_km for rule in rules if rule.interval_km),
        start=Decimal("0"),
    )


def evaluate_maintenance(db: Session, vehicle: Vehicle, today: date | None = None) -> None:
    evaluation_date = today or date.today()
    rules = db.scalars(
        select(MaintenanceRule).where(
            MaintenanceRule.vehicle_id == vehicle.id,
            MaintenanceRule.active.is_(True),
        )
    )
    for rule in rules:
        latest = _latest_execution(db, rule.id)
        base_odometer = latest.odometer_km if latest else rule.baseline_odometer_km
        base_date = latest.performed_at if latest else rule.baseline_date
        due_odometer = base_odometer + rule.interval_km if rule.interval_km else None
        due_date = base_date + timedelta(days=rule.interval_days) if rule.interval_days else None

        severity: str | None = None
        if due_odometer is not None:
            if vehicle.odometer_km >= due_odometer:
                severity = "critical"
            elif vehicle.odometer_km >= due_odometer - rule.warning_km:
                severity = "warning"
        if due_date is not None:
            date_severity = None
            if evaluation_date >= due_date:
                date_severity = "critical"
            elif evaluation_date >= due_date - timedelta(days=rule.warning_days):
                date_severity = "warning"
            if date_severity == "critical" or severity is None:
                severity = date_severity or severity

        open_alert = db.scalar(
            select(MaintenanceAlert).where(
                MaintenanceAlert.rule_id == rule.id,
                MaintenanceAlert.status == "open",
            )
        )
        if severity is None:
            if open_alert:
                open_alert.status = "resolved"
                open_alert.resolved_at = datetime.now(UTC)
                _emit_event(db, open_alert, "maintenance.alert.resolved")
            continue

        message = f"{rule.name}: manutenção {('vencida' if severity == 'critical' else 'próxima')}"
        if open_alert is None:
            open_alert = MaintenanceAlert(
                organization_id=rule.organization_id,
                vehicle_id=vehicle.id,
                rule_id=rule.id,
                severity=severity,
                due_odometer_km=due_odometer,
                due_date=due_date,
                message=message,
            )
            db.add(open_alert)
            db.flush()
            _emit_event(db, open_alert, "maintenance.alert.created")
        elif open_alert.severity != severity:
            open_alert.severity = severity
            open_alert.message = message
            open_alert.updated_at = datetime.now(UTC)
            _emit_event(db, open_alert, "maintenance.alert.updated")


def _emit_event(db: Session, alert: MaintenanceAlert, event_type: str) -> None:
    db.add(
        OutboxEvent(
            organization_id=alert.organization_id,
            event_type=event_type,
            aggregate_type="maintenance_alert",
            aggregate_id=alert.id,
            payload={
                "alert_id": str(alert.id),
                "vehicle_id": str(alert.vehicle_id),
                "rule_id": str(alert.rule_id),
                "severity": alert.severity,
                "status": alert.status,
                "message": alert.message,
            },
        )
    )
