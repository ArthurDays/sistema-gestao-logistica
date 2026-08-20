import hashlib
import hmac
import json
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import OutboxEvent
from app.outbox import deliver_pending_events


def test_outbox_delivery_is_signed_and_idempotent(db_session: Session, monkeypatch) -> None:
    monkeypatch.setattr(settings, "n8n_webhook_url", "https://n8n.test/webhook")
    monkeypatch.setattr(settings, "n8n_webhook_secret", "secret-for-test")
    event = OutboxEvent(
        organization_id=uuid4(),
        event_type="maintenance.alert.created",
        aggregate_type="maintenance_alert",
        aggregate_id=uuid4(),
        payload={"severity": "critical"},
        created_at=datetime.now(UTC),
    )
    db_session.add(event)
    db_session.commit()
    captured: dict[str, object] = {}

    def sender(url: str, body: bytes, headers: dict[str, str]) -> None:
        captured.update(url=url, body=body, headers=headers)

    assert deliver_pending_events(db_session, sender) == 1
    assert deliver_pending_events(db_session, sender) == 0
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Idempotency-Key"] == str(event.id)
    assert headers["X-Logistica-Signature"] == "sha256=" + hmac.new(
        b"secret-for-test", captured["body"], hashlib.sha256
    ).hexdigest()
    assert json.loads(captured["body"])["id"] == str(event.id)
    db_session.refresh(event)
    assert event.status == "delivered"
    assert event.attempts == 1
