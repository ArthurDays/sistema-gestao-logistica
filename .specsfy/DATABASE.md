# Banco de dados

Mapa de persistência observado nos models SQLAlchemy, migrations Alembic e
serviços declarados. Não contém dados nem credenciais.

## Fontes de dados

<!-- specsfy:database:start -->
| Fonte | Tecnologia/forma | Evidência |
| --- | --- | --- |
| Domínio LogiSync | PostgreSQL 18 / SQLAlchemy / Alembic | `backend/app/models.py`, `backend/alembic/versions/` |
| Metabase metadata | PostgreSQL 18, banco separado e administrativo local | `docker-compose.yml`, `infra/postgres/init-bi.sh` |
| Catálogo de referência | Google Sheets exportada como CSV; espelho somente leitura no domínio | `backend/app/catalog.py`, `docker-compose.yml` |
| Automação n8n | Volume Docker próprio; integração no domínio somente pela API/outbox | `docker-compose.yml`, `backend/app/outbox_worker.py` |

## Estruturas detectadas

| Estrutura | Tipo | Campos | Relações | Fonte |
| --- | --- | --- | --- | --- |
| `organizations` | tabela de domínio | `id UUID PK`; `name varchar(160)`; `timezone varchar(64)`; `created_at timestamptz` | raiz de ownership das entidades tenant-aware | `Organization` |
| `users` | tabela de autenticação | `id UUID PK`; `organization_id UUID FK`; `email varchar(320) UQ`; `password_hash varchar(255)`; `google_subject varchar(255) UQ nullable`; `role varchar(20)`; `active bool`; `created_at timestamptz` | N:1 `organizations`; 1:N `oauth_exchange_codes` | `User`, migrations `0001`, `0010` |
| `oauth_exchange_codes` | estado efêmero de autenticação | `id UUID PK`; `code_hash varchar(64) UQ`; `user_id UUID FK`; `expires_at timestamptz`; `used_at timestamptz nullable`; `created_at timestamptz` | N:1 `users`; índices em hash, usuário e expiração | `OAuthExchangeCode`, migration `0011` |
| `auth_login_throttles` | estado efêmero de proteção | `id UUID PK`; `scope varchar(20)`; `key_hash varchar(64)`; `attempt_count int`; `window_started_at timestamptz`; `blocked_until timestamptz nullable`; `updated_at timestamptz` | UQ `(scope,key_hash)`; índice em bloqueio; não guarda e-mail/IP | `AuthLoginThrottle`, migration `0011` |
| `vehicle_catalog_specs` | referência técnica espelhada | `id UUID PK`; categoria, marca, modelo, versão, powertrain, ano e combustível; consumos/tanque/custos `NUMERIC`; intervalos `int`; `active`; `synced_at` | UQ `(brand,model,version)`; 1:N `vehicles` | `VehicleCatalogSpec`, migration `0003` |
| `vehicles` | agregado de frota | `id UUID PK`; `catalog_spec_id UUID nullable`; `organization_id UUID FK`; nome/placa/categoria/energia; odômetro/tanque/consumo `NUMERIC`; status; criação | N:1 organização e catálogo; 1:N registros/despesas/manutenção | `Vehicle`, migrations `0001`, `0003` |
| `operational_records` | fechamento operacional | `id UUID PK`; organização/veículo FKs; data; odômetros/distância/receita/combustível/manutenção/lucro `NUMERIC`; notas; idempotência; criação | N:1 organização/veículo; UQ organização+idempotência; checks não negativos | `OperationalRecord`, migration `0001` |
| `expenses` | despesas | `id UUID PK`; organização FK; veículo FK nullable; data; categoria; valor `NUMERIC(14,2)`; descrição; criação | N:1 organização/veículo; valor positivo | `Expense`, migration `0001` |
| `fuel_prices` | preços de combustível | `id UUID PK`; organização FK; localidade; energia; preço `NUMERIC(10,3)`; vigência; fonte; coleta | lookup por organização/local/energia/data | `FuelPrice`, migration `0001` |
| `integration_receipts` | idempotência de integrações | `id UUID PK`; organização FK; chave; fonte; tipo/id de recurso; payload JSON; criação | UQ organização+chave; índice organização+criação | `IntegrationReceipt`, migration `0002` |
| `maintenance_rules` | regras preventivas | `id UUID PK`; organização/veículo FKs; nome; intervalos; custo/avisos/baseline; ativo; criação | exige intervalo KM ou dias; custo não negativo | `MaintenanceRule`, migration `0004` |
| `maintenance_executions` | execuções de manutenção | `id UUID PK`; organização/veículo/regra FKs; data; odômetro; custo; fornecedor; notas; criação | N:1 regra/veículo/organização; checks não negativos | `MaintenanceExecution`, migration `0004` |
| `maintenance_alerts` | alertas derivados | `id UUID PK`; organização/veículo/regra FKs; severidade/status; vencimentos; mensagem; timestamps | índice organização+status | `MaintenanceAlert`, migration `0004` |
| `outbox_events` | entrega assíncrona | `id UUID PK`; organização FK; tipo de evento/agregado; agregado UUID; payload JSON; status; tentativas; timestamps | índice status+criação; worker envia via webhook assinado | `OutboxEvent`, migration `0005` |
<!-- specsfy:database:end -->

## Decisões, ownership e retenção

- O banco de domínio pertence à API; n8n não possui escrita direta nas tabelas.
- Toda entidade operacional é vinculada a `organization_id`; consultas da API
  aplicam o tenant autenticado.
- `oauth_exchange_codes` retém apenas hash e expira em dois minutos; códigos
  consumidos não voltam a ser aceitos. Registros expirados há mais de um dia
  são removidos oportunisticamente durante trocas válidas.
- `auth_login_throttles` usa chaves HMAC para identidade/origem, janela e
  bloqueio de 15 minutos; não persiste identificadores brutos. Registros
  inativos há mais de um dia são removidos oportunisticamente no login.
- O papel `metabase_bi` é leitura global exclusivamente administrativa local.
  Uso tenant-facing exige outra arquitetura com isolamento por organização.
- Valores financeiros permanecem em `NUMERIC`/`Decimal`; não usar `float`.
