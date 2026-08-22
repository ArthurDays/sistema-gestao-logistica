import csv
import re
from datetime import UTC, datetime
from decimal import Decimal
from io import StringIO
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import VehicleCatalogSpec

CATALOG_HEADERS = (
    "Categoria",
    "Marca",
    "Modelo Base",
    "Versão / Trim Exato",
    "Motorização / Câmbio",
    "Ano/Modelo",
    "Combustível",
    "Consumo Gasolina (km/l)",
    "Consumo Álcool (km/l)",
    "Tanque (L)",
    "Custo Tanque Est. (Gas)",
    "Troca Óleo (km)",
    "Custo Óleo (R$)",
    "Troca Pneu (km)",
)
CATALOG_CATEGORIES = {"Carro", "Moto", "Caminhão", "Ônibus"}
MODEL_YEAR_PATTERN = re.compile(r"^\d{4}/\d{4}$")


def _decimal(value: str | None) -> Decimal | None:
    normalized = (value or "").strip().replace(",", ".")
    return Decimal(normalized) if normalized else None


def _integer(value: str | None) -> int | None:
    normalized = (value or "").strip()
    if not normalized:
        return None
    number = Decimal(normalized.replace(",", "."))
    if number != number.to_integral_value():
        raise ValueError(f"valor inteiro inválido: {value}")
    return int(number)


def _align_catalog_row(raw_row: list[str], previous_category: str | None, line_number: int) -> list[str]:
    row = [value.strip() for value in raw_row]
    while row and not row[-1]:
        row.pop()
    explicit_category = bool(row and row[0] in CATALOG_CATEGORIES)
    if explicit_category:
        category = row[0]
        identity_start = 1
    elif previous_category is not None:
        category = previous_category
        identity_start = 0
    else:
        raise ValueError(f"linha {line_number}: categoria ausente ou desconhecida")

    if len(row) < identity_start + 4:
        raise ValueError(f"linha {line_number}: colunas insuficientes")
    brand, model, version = row[identity_start : identity_start + 3]
    powertrain_start = identity_start + 3
    year_indexes = [
        index for index in range(powertrain_start, len(row)) if MODEL_YEAR_PATTERN.fullmatch(row[index])
    ]
    if len(year_indexes) != 1:
        raise ValueError(f"linha {line_number}: ano/modelo não identifica o alinhamento")
    year_index = year_indexes[0]
    tail = row[year_index:]
    if len(tail) != 9:
        raise ValueError(f"linha {line_number}: quantidade de colunas incompatível")
    powertrain_parts = row[powertrain_start:year_index]
    if not brand or not model or not powertrain_parts:
        raise ValueError(f"linha {line_number}: identidade técnica incompleta")
    powertrain = ",".join(powertrain_parts).replace("\\,", ",")
    return [category, brand, model, version, powertrain, *tail]


def parse_catalog(csv_text: str) -> list[dict[str, object]]:
    reader = csv.reader(StringIO(csv_text))
    try:
        raw_headers = [header.strip() for header in next(reader)]
    except StopIteration as error:
        raise ValueError("A planilha não possui cabeçalho") from error
    while raw_headers and not raw_headers[-1]:
        raw_headers.pop()
    headers = tuple(raw_headers)
    if headers != CATALOG_HEADERS:
        raise ValueError("O cabeçalho da planilha não corresponde ao catálogo esperado")

    rows: list[dict[str, object]] = []
    previous_category: str | None = None
    for line_number, raw_row in enumerate(reader, start=2):
        if not any(value.strip() for value in raw_row):
            continue
        aligned = _align_catalog_row(raw_row, previous_category, line_number)
        previous_category = aligned[0]
        source = dict(zip(CATALOG_HEADERS, aligned, strict=True))
        try:
            rows.append(
                {
                    "category": source["Categoria"],
                    "brand": source["Marca"],
                    "model": source["Modelo Base"],
                    "version": source["Versão / Trim Exato"] or "Padrão",
                    "powertrain": source["Motorização / Câmbio"] or "Não informado",
                    "model_year": source["Ano/Modelo"],
                    "fuel_type": source["Combustível"] or "Não informado",
                    "gasoline_consumption_km_l": _decimal(source["Consumo Gasolina (km/l)"]),
                    "ethanol_consumption_km_l": _decimal(source["Consumo Álcool (km/l)"]),
                    "tank_capacity_l": _decimal(source["Tanque (L)"]),
                    "estimated_tank_cost": _decimal(source["Custo Tanque Est. (Gas)"]),
                    "oil_change_km": _integer(source["Troca Óleo (km)"]),
                    "oil_change_cost": _decimal(source["Custo Óleo (R$)"]),
                    "tire_change_km": _integer(source["Troca Pneu (km)"]),
                }
            )
        except (ArithmeticError, ValueError) as error:
            raise ValueError(f"linha {line_number}: valor técnico inválido: {error}") from error
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
