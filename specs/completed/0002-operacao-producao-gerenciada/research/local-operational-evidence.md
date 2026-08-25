# Evidência operacional local

## Escopo

Registro das fontes locais usadas para definir e validar a operação gerenciada.
Nenhuma documentação externa foi consultada e nenhum valor de segredo foi
copiado para este artefato.

## Fontes verificadas

- `docker-compose.yml`: ambiente local e health checks.
- `.github/workflows/ci.yml`: gates de backend e frontend.
- `infra/hosting/production.env.example`: contrato público de Netlify e Render.
- `infra/hosting/validate-production-config.ps1`: rejeição de configuração insegura.
- `infra/postgres/backup.ps1` e `infra/postgres/restore-check.ps1`: recuperação isolada.
- `backend/tests/production/test_production_contracts.py`: contratos executáveis AC-001 a AC-003.
- `docs/runbook.md`: deploy, rollback, backup e resposta a incidentes.

## Resultado observado

Os três contratos de produção passaram, a restauração foi exercitada em
banco descartável e o runbook permaneceu sem credenciais ou valores reais.
