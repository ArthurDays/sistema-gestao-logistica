FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS test
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests
CMD ["sh", "-c", "pytest && ruff check app tests && mypy app"]

FROM base AS runtime
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
