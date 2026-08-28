# Evidência local da implementação

## Escopo

Índice das fontes locais usadas para definir e validar a recuperação segura de
senha. Nenhuma documentação externa, credencial ou dado real foi incluído.

## Segurança do token

- `backend/app/password_reset.py`: geração aleatória, persistência SHA-256,
  expiração, throttle, consumo único e transporte SMTP injetável.
- `backend/alembic/versions/20260826_0012_password_reset.py`: schema hash-only,
  índices e downgrade.
- `backend/tests/test_password_reset.py`: critérios AC-001 a AC-004.
- `backend/tests/test_password_reset_service.py`: concorrência e falha SMTP.
- `backend/tests/test_password_reset_migration.py`: contrato da migration.

## Interface e operação

- `frontend/components/operations-dashboard.tsx`: solicitação, confirmação e
  remoção do token da URL.
- `docker-compose.yml`: configuração SMTP e gate `api-tests` com código-fonte
  somente leitura.
- `docs/runbook.md`: configuração, deploy e diagnóstico sanitizado.

## Resultado observado

As suítes local e em container, a rastreabilidade integral e os health checks
confirmaram o comportamento descrito na fonte normativa.
