# Banco de dados

<!-- specsfy:documentator:start -->
## Fontes de persistência

| Arquivo |
| --- |
| backend\.mypy_cache\3.12\pydantic\_migration.data.json |
| backend\.mypy_cache\3.12\pydantic\_migration.meta.json |
| backend\tests\test_bi_migration.py |
| Nenhuma estrutura confirmada além das fontes listadas. |

```mermaid
erDiagram
  ENTITY { string id }
```
<!-- specsfy:documentator:end -->

## Acesso somente leitura para BI

A migration `backend/alembic/versions/20260821_0009_bi_views.py` publica duas projeções:

| View | Finalidade | Fonte principal |
| --- | --- | --- |
| `bi_vehicle_daily` | Operação diária, distância, receita, custos e lucro por veículo | `operational_records` e `vehicles` |
| `bi_maintenance_alerts` | Alertas de manutenção com veículo, severidade, vencimento e resolução | `maintenance_alerts` e `vehicles` |

O papel `metabase_bi` recebe `CONNECT`, `USAGE` no schema `public` e `SELECT` somente nessas views. Ele não recebe privilégios nas tabelas de domínio. O script `infra/postgres/init-bi.sh` cria ou atualiza os papéis de forma idempotente e usa parâmetros do `psql` para tratar identificadores e senhas sem interpolação SQL insegura.
