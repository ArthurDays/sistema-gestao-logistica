import hashlib
import hmac
import json
from datetime import UTC, datetime
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import OutboxEvent


class WebhookSender(Protocol):
    def __call__(self, url: str, body: bytes, headers: dict[str, str]) -> None: ...


def _send_webhook(url: str, body: bytes, headers: dict[str, str]) -> None:
    request = Request(url, data=body, headers=headers, method="POST")
    with urlopen(request, timeout=10) as response:  # noqa: S310 - destination is explicit configuration
        if not 200 <= response.status < 300:
            raise RuntimeError(f"Webhook respondeu HTTP {response.status}")


def deliver_pending_events(db: Session, sender: WebhookSender = _send_webhook) -> int:
    """Deliver each pending outbox event at most once per invocation.

    n8n receives a stable Idempotency-Key, so retrying a failed delivery cannot
    duplicate the downstream notification.
    """
    if not settings.n8n_webhook_url or not settings.n8n_webhook_secret:
        return 0

    events = db.scalars(
        select(OutboxEvent)
        .where(
            OutboxEvent.status == "pending",
            OutboxEvent.attempts < settings.outbox_max_attempts,
        )
        .order_by(OutboxEvent.created_at)
        .with_for_update(skip_locked=True)
    ).all()
    delivered = 0
    for event in events:
        body = json.dumps(
            {
                "id": str(event.id),
                "type": event.event_type,
                "organization_id": str(event.organization_id),
                "aggregate_type": event.aggregate_type,
                "aggregate_id": str(event.aggregate_id),
                "payload": event.payload,
                "occurred_at": event.created_at.isoformat(),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        signature = hmac.new(settings.n8n_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        event.attempts += 1
        try:
            sender(
                settings.n8n_webhook_url,
                body,
                {
                    "Content-Type": "application/json",
                    "Idempotency-Key": str(event.id),
                    "X-Logistica-Signature": f"sha256={signature}",
                    "X-Logistica-Event": event.event_type,
                },
            )
        except (HTTPError, URLError, OSError, RuntimeError):
            continue
        event.status = "delivered"
        event.processed_at = datetime.now(UTC)
        delivered += 1
    db.commit()
    return delivered
