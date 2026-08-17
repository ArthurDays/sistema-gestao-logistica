import csv
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import VehicleCatalogSpec


def _decimal(value: str | None) -> Decimal | None:
    normalized = (value or "").strip().replace(",", ".")
    return Decimal(normalized) if normalized else None


def _integer(value: str | None) -> int | None:
    normalized = (value or "").strip()
    return int(normalized) if normalized else None


def parse_catalog(csv_text: str) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for source in csv.DictReader(StringIO(csv_text)):
        if not source.get("Marca") or not source.get("Modelo Base"):
            continue
        rows.append(
            {
                "category": (source.get("Categoria") or "Outro").strip(),
                "brand": source["Marca"].strip(),
                "model": source["Modelo Base"].strip(),
                "version": (source.get("Versão / Trim Exato") or "Padrão").strip(),
                "powertrain": (source.get("Motorização / Câmbio") or "Não informado").strip(),
                "model_year": (source.get("Ano/Modelo") or "Não informado").strip(),
                "fuel_type": (source.get("Combustível") or "Não informado").strip(),
                "gasoline_consumption_km_l": _decimal(source.get("Consumo Gasolina (km/l)")),
                "ethanol_consumption_km_l": _decimal(source.get("Consumo Álcool (km/l)")),
                "tank_capacity_l": _decimal(source.get("Tanque (L)")),
                "estimated_tank_cost": _decimal(source.get("Custo Tanque Est. (Gas)")),
                "oil_change_km": _integer(source.get("Troca Óleo (km)")),
                "oil_change_cost": _decimal(source.get("Custo Óleo (R$)")),
                "tire_change_km": _integer(source.get("Troca Pneu (km)")),
            }
        )
    if not rows:
        raise ValueError("A planilha não possui linhas válidas no catálogo")
    return rows


def fetch_catalog() -> list[dict[str, object]]:
    parsed_url = urlparse(settings.vehicle_catalog_csv_url)
    if parsed_url.scheme != "https" or parsed_url.hostname != "docs.google.com":
        raise ValueError("A URL do catálogo deve usar HTTPS no domínio docs.google.com")
    request = Request(settings.vehicle_catalog_csv_url, headers={"User-Agent": "LogisticaCatalog/1.0"})
    with urlopen(request, timeout=20) as response:  # noqa: S310 - host validated above
        return parse_catalog(response.read().decode("utf-8-sig"))


def sync_catalog(db: Session) -> tuple[int, int, int]:
    source_rows = fetch_catalog()
    db.execute(update(VehicleCatalogSpec).values(active=False))
    imported = 0
    updated = 0
    synced_at = datetime.now(UTC)
    for values in source_rows:
        spec = db.scalar(
            select(VehicleCatalogSpec).where(
                VehicleCatalogSpec.brand == values["brand"],
                VehicleCatalogSpec.model == values["model"],
                VehicleCatalogSpec.version == values["version"],
            )
        )
        if spec is None:
            spec = VehicleCatalogSpec(**values)
            db.add(spec)
            imported += 1
        else:
            for field, value in values.items():
                setattr(spec, field, value)
            updated += 1
        spec.active = True
        spec.synced_at = synced_at
    db.commit()
    return imported, updated, len(source_rows)
