# Testes

<!-- specsfy:documentator:start -->
## Resumo

- Arquivos de teste: 0.
- Runner: não identificado.
- Scripts: não declarados.

| Arquivo |
| --- |
| Nenhum teste identificado |
<!-- specsfy:documentator:end -->

## Contrato e smoke test de BI

- `backend/tests/test_bi_migration.py` verifica que a migration cria somente as duas views esperadas, concede apenas `SELECT` ao papel de BI e mantém a ordem segura no downgrade.
- O smoke test de T024 aplica todas as migrations em PostgreSQL 18 descartável, repete o bootstrap, conecta como `metabase_bi`, consulta as views e confirma a negação de acesso às tabelas-base.
- Evidência de 2026-08-24: `daily=0`, `alerts=0`, `view_grants=2` e `base_grants=0` no banco recém-criado.
