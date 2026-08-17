# Modelo de dados

```mermaid
erDiagram
    ORGANIZATION ||--o{ VEHICLE : possui
    VEHICLE_CATALOG_SPEC ||--o{ VEHICLE : referencia
    VEHICLE ||--o{ OPERATIONAL_RECORD : realiza
    VEHICLE ||--o{ EXPENSE : gera
    VEHICLE ||--o{ MAINTENANCE_RULE : possui
    MAINTENANCE_RULE ||--o{ MAINTENANCE_EXECUTION : registra
    MAINTENANCE_RULE ||--o{ MAINTENANCE_ALERT : dispara

    VEHICLE {
      uuid id PK
      uuid organization_id FK
      uuid catalog_spec_id FK
      string name
      string plate
      decimal odometer_km
      decimal average_consumption
      string status
    }
    OPERATIONAL_RECORD {
      uuid id PK
      uuid vehicle_id FK
      date operation_date
      decimal odometer_start_km
      decimal odometer_end_km
      decimal distance_km
      decimal gross_revenue
      decimal fuel_cost
      decimal maintenance_cost
      decimal net_profit
      string idempotency_key
    }
    MAINTENANCE_RULE {
      uuid id PK
      uuid vehicle_id FK
      decimal interval_km
      int interval_days
      decimal estimated_cost
      decimal warning_km
    }
```

## Invariantes

- `odometer_end_km >= vehicle.odometer_km`.
- `distance_km = odometer_end_km - odometer_start_km`.
- Valores monetários e métricos são `NUMERIC`/`Decimal`.
- A chave de idempotência impede duplicidade de fechamento.
- Registros preservam custos históricos; mudanças na base não reescrevem o passado.

## Migrations

`backend/alembic/versions/` é a trilha oficial do schema. Não substitua migrations por alterações manuais no DBeaver.
