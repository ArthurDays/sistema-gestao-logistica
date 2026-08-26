# Banco de dados

<!-- specsfy:documentator:start -->
## Fontes de persistência

| Arquivo |
| --- |
| backend\.mypy_cache\3.12\pydantic\_migration.data.json |
| backend\.mypy_cache\3.12\pydantic\_migration.meta.json |
| backend\tests\test_auth_hardening_migration.py |
| backend\tests\test_bi_migration.py |
| Nenhuma estrutura confirmada além das fontes listadas. |

```mermaid
erDiagram
  ENTITY { string id }
```
<!-- specsfy:documentator:end -->

## Acesso somente leitura para BI

A migration `backend/alembic/versions/20260821_0009_bi_views.py` publica
`bi_vehicle_daily` e `bi_maintenance_alerts`. O papel `metabase_bi` recebe
somente leitura nessas views e é reservado ao Metabase administrativo local.
Ele não é uma fronteira de isolamento tenant-facing.

## Estado de autenticação

| Tabela | Conteúdo permitido | Retenção lógica |
| --- | --- | --- |
| `oauth_exchange_codes` | hash, usuário, expiração e consumo | dois minutos; uso único |
| `auth_login_throttles` | escopo, chave HMAC, contagem e bloqueio | janela/bloqueio de 15 minutos |

Nenhuma delas armazena código OAuth, e-mail ou IP em texto claro. O inventário
completo de tabelas, campos, relações, constraints e retenção está em
`.specsfy/DATABASE.md`. Estados expirados há mais de um dia são limpos
oportunisticamente pelos fluxos de autenticação.
