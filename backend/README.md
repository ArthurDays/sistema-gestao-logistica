# Backend

API FastAPI responsável pelas regras de negócio e persistência.

```text
app/api.py          endpoints e coordenação transacional
app/models.py       modelos SQLAlchemy
app/schemas.py      contratos Pydantic
app/maintenance.py cálculo preventivo e alertas
app/catalog.py      importação e normalização do catálogo
app/core/           configuração da aplicação
alembic/            migrations do PostgreSQL
tests/              cenários de domínio e API
```

Para validar isoladamente, use `docker compose --profile test run --rm api-tests` na raiz.
