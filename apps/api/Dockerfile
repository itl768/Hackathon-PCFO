# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml .python-version ./

RUN uv sync --no-dev --no-install-project

COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
RUN uv sync --no-dev

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/alembic /app/alembic
COPY --from=builder /app/alembic.ini /app/alembic.ini

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN mkdir -p /var/invoice_documents

EXPOSE 8000

CMD ["sh", "-c", "api migrate && uvicorn api.main:app --host 0.0.0.0 --port 8000"]
