# Evidência técnica local

## Escopo

Registro das fontes locais já usadas na entrega da SPEC-0001. Nenhuma fonte
externa, credencial ou dado real foi copiado para este artefato.

## Google Sheets read-only

- `backend/app/catalog_sync.py`: lê o catálogo externo e atualiza somente a
  projeção técnica autorizada.
- `backend/tests/test_catalog_sync.py`: cobre a sincronização e seus limites.
- `.specsfy/RULES.md`: mantém a API como fronteira obrigatória das integrações.

## PostgreSQL BI read-only

- `backend/alembic/versions/20250824_0002_bi_views.py`: cria as views de BI.
- `backend/tests/test_bi_migration.py`: valida views, grants e reversibilidade.
- `infra/postgres/init-bi.sh`: configura o papel de leitura usado pelo Metabase.

## Resultado observado

As fontes executáveis sustentam as duas claims críticas já aceitas: o catálogo
externo permanece uma entrada controlada e o acesso de BI ao PostgreSQL é
restrito à leitura.
