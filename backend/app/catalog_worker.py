import logging
from threading import Event

from app.catalog import sync_catalog
from app.core.config import settings
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("catalog-sync")


def run() -> None:
    interval = max(settings.catalog_sync_interval_seconds, 60)
    while True:
        with SessionLocal() as db:
            try:
                imported, updated, total = sync_catalog(db)
                logger.info(
                    "Catálogo sincronizado: total=%d novos=%d atualizados=%d",
                    total,
                    imported,
                    updated,
                )
            except Exception:
                db.rollback()
                logger.exception("Falha na sincronização do catálogo; mantendo o espelho anterior")
        Event().wait(interval)


if __name__ == "__main__":
    run()
