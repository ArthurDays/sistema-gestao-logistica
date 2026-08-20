import time

from app.core.config import settings
from app.db import SessionLocal
from app.outbox import deliver_pending_events


def main() -> None:
    while True:
        with SessionLocal() as db:
            deliver_pending_events(db)
        time.sleep(settings.outbox_poll_interval_seconds)


if __name__ == "__main__":
    main()
