FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY alembic.ini ./
COPY alembic ./alembic
COPY evals ./evals
COPY src ./src

RUN uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uvicorn", "adaptive_rag.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
