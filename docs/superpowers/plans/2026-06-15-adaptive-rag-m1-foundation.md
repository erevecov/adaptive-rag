# Adaptive RAG M1 Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the Python project foundation for Adaptive RAG: package layout, settings, logging, DB session/Alembic base, FastAPI health endpoint, Typer CLI shell, and quality gates.

**Architecture:** This milestone creates infrastructure only. API and CLI are thin entrypoints; shared configuration lives in `adaptive_rag.config`; database connection code lives in `adaptive_rag.db`; no RAG, providers, ingestion, or retrieval behavior is implemented yet.

**Tech Stack:** Python 3.12, uv, FastAPI, Typer, Rich, Pydantic Settings, SQLAlchemy 2, Alembic, psycopg, pytest, httpx, ruff, mypy.

---

## Scope

This plan covers only Milestone 1. It intentionally does not implement domain tables, ingestion jobs, LlamaIndex, Unstructured, Voyage, DeepSeek, pgvector models, Qdrant, chat orchestration, or evals. Those belong in later plans.

## Target File Structure

Files created in this milestone:

```txt
pyproject.toml
.gitignore
.env.example
README.md
alembic.ini
alembic/env.py
alembic/versions/.gitkeep
src/adaptive_rag/__init__.py
src/adaptive_rag/api/__init__.py
src/adaptive_rag/api/app.py
src/adaptive_rag/api/routes/__init__.py
src/adaptive_rag/api/routes/health.py
src/adaptive_rag/cli/__init__.py
src/adaptive_rag/cli/app.py
src/adaptive_rag/config/__init__.py
src/adaptive_rag/config/logging.py
src/adaptive_rag/config/settings.py
src/adaptive_rag/db/__init__.py
src/adaptive_rag/db/base.py
src/adaptive_rag/db/session.py
tests/unit/config/test_settings.py
tests/unit/db/test_session.py
tests/integration/api/test_health.py
tests/integration/cli/test_cli.py
```

---

### Task 1: Project Package Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `README.md`
- Create: `src/adaptive_rag/__init__.py`
- Create: package `__init__.py` files under `api`, `api/routes`, `cli`, `config`, and `db`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "adaptive-rag"
version = "0.1.0"
description = "Personal, project-scoped adaptive RAG system."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.14",
  "fastapi>=0.115",
  "httpx>=0.28",
  "pgvector>=0.3",
  "psycopg[binary]>=3.2",
  "pydantic-settings>=2.6",
  "rich>=13.9",
  "sqlalchemy>=2.0",
  "typer>=0.15",
  "uvicorn[standard]>=0.32",
]

[project.optional-dependencies]
dev = [
  "mypy>=1.13",
  "pytest>=8.3",
  "pytest-asyncio>=0.24",
  "ruff>=0.8",
]

[project.scripts]
adaptive-rag = "adaptive_rag.cli.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/adaptive_rag"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-q"

[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]

[tool.mypy]
python_version = "3.12"
strict = true
packages = ["adaptive_rag"]
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
.env
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
*.pyc
*.pyo
*.pyd
*.egg-info/
dist/
build/
.coverage
htmlcov/
```

- [ ] **Step 3: Create `.env.example`**

```dotenv
ADAPTIVE_RAG_ENV=local
ADAPTIVE_RAG_LOG_LEVEL=INFO
ADAPTIVE_RAG_DATABASE_URL=postgresql+psycopg://adaptive_rag:adaptive_rag@localhost:5432/adaptive_rag
ADAPTIVE_RAG_API_KEY=
ADAPTIVE_RAG_VECTOR_STORE=pgvector
```

- [ ] **Step 4: Create `README.md`**

````markdown
# Adaptive RAG

Personal, project-scoped RAG system for learning and portfolio use.

## Local Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
```
````

- [ ] **Step 5: Create package init files**

```python
# src/adaptive_rag/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create empty files:

```txt
src/adaptive_rag/api/__init__.py
src/adaptive_rag/api/routes/__init__.py
src/adaptive_rag/cli/__init__.py
src/adaptive_rag/config/__init__.py
src/adaptive_rag/db/__init__.py
```

- [ ] **Step 6: Sync dependencies**

Run:

```bash
uv sync --extra dev
```

Expected: command exits with code `0` and creates `.venv`.

- [ ] **Step 7: Verify package import**

Run:

```bash
uv run python -c "import adaptive_rag; print(adaptive_rag.__version__)"
```

Expected output:

```txt
0.1.0
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml .gitignore .env.example README.md src/adaptive_rag
git commit -m "chore: scaffold adaptive rag package"
```

---

### Task 2: Settings and Logging

**Files:**
- Create: `src/adaptive_rag/config/settings.py`
- Create: `src/adaptive_rag/config/logging.py`
- Create: `tests/unit/config/test_settings.py`

- [ ] **Step 1: Write failing settings tests**

```python
# tests/unit/config/test_settings.py
from adaptive_rag.config.settings import Settings


def test_settings_use_adaptive_rag_env_prefix(monkeypatch):
    monkeypatch.setenv("ADAPTIVE_RAG_ENV", "test")
    monkeypatch.setenv("ADAPTIVE_RAG_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    monkeypatch.setenv("ADAPTIVE_RAG_VECTOR_STORE", "pgvector")

    settings = Settings()

    assert settings.env == "test"
    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert settings.vector_store == "pgvector"


def test_api_key_is_optional(monkeypatch):
    monkeypatch.delenv("ADAPTIVE_RAG_API_KEY", raising=False)

    settings = Settings()

    assert settings.api_key is None
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/unit/config/test_settings.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `adaptive_rag.config.settings`.

- [ ] **Step 3: Implement settings**

```python
# src/adaptive_rag/config/settings.py
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


VectorStoreName = Literal["pgvector", "qdrant"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ADAPTIVE_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "local"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://adaptive_rag:adaptive_rag"
        "@localhost:5432/adaptive_rag"
    )
    api_key: str | None = Field(default=None)
    vector_store: VectorStoreName = "pgvector"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Implement logging configuration**

```python
# src/adaptive_rag/config/logging.py
import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
```

- [ ] **Step 5: Run settings tests**

Run:

```bash
uv run pytest tests/unit/config/test_settings.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Run lint for config package**

Run:

```bash
uv run ruff check src/adaptive_rag/config tests/unit/config
```

Expected: command exits with code `0`.

- [ ] **Step 7: Commit**

```bash
git add src/adaptive_rag/config tests/unit/config
git commit -m "feat: add application settings"
```

---

### Task 3: Database Session and Alembic Base

**Files:**
- Create: `src/adaptive_rag/db/base.py`
- Create: `src/adaptive_rag/db/session.py`
- Create: `tests/unit/db/test_session.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/.gitkeep`

- [ ] **Step 1: Write failing DB session tests**

```python
# tests/unit/db/test_session.py
from sqlalchemy import text

from adaptive_rag.db.base import Base
from adaptive_rag.db.session import create_engine_from_url, create_session_factory


def test_base_metadata_starts_empty():
    assert Base.metadata.tables == {}


def test_sqlite_engine_can_execute_query():
    engine = create_engine_from_url("sqlite+pysqlite:///:memory:")
    session_factory = create_session_factory(engine)

    with session_factory() as session:
        value = session.execute(text("select 1")).scalar_one()

    assert value == 1
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/unit/db/test_session.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `adaptive_rag.db.base` or `adaptive_rag.db.session`.

- [ ] **Step 3: Implement SQLAlchemy base**

```python
# src/adaptive_rag/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 4: Implement DB session helpers**

```python
# src/adaptive_rag/db/session.py
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from adaptive_rag.config.settings import get_settings


def create_engine_from_url(database_url: str) -> Engine:
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


engine = create_engine_from_url(get_settings().database_url)
SessionLocal = create_session_factory(engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session
```

- [ ] **Step 5: Create Alembic config**

```ini
# alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
path_separator = os

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

- [ ] **Step 6: Create Alembic env**

```python
# alembic/env.py
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 7: Keep Alembic versions directory**

Create empty file:

```txt
alembic/versions/.gitkeep
```

- [ ] **Step 8: Run DB tests**

Run:

```bash
uv run pytest tests/unit/db/test_session.py -q
```

Expected: `2 passed`.

- [ ] **Step 9: Run Alembic syntax check**

Run:

```bash
uv run python -m py_compile alembic/env.py
```

Expected: command exits with code `0`.

- [ ] **Step 10: Commit**

```bash
git add src/adaptive_rag/db tests/unit/db alembic.ini alembic
git commit -m "feat: add database session foundation"
```

---

### Task 4: FastAPI Health Endpoint

**Files:**
- Create: `src/adaptive_rag/api/app.py`
- Create: `src/adaptive_rag/api/routes/health.py`
- Create: `tests/integration/api/test_health.py`

- [ ] **Step 1: Write failing API test**

```python
# tests/integration/api/test_health.py
from fastapi.testclient import TestClient

from adaptive_rag.api.app import create_app


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "adaptive-rag"}
```

- [ ] **Step 2: Run API test to verify failure**

Run:

```bash
uv run pytest tests/integration/api/test_health.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `adaptive_rag.api.app`.

- [ ] **Step 3: Implement health route**

```python
# src/adaptive_rag/api/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "adaptive-rag"}
```

- [ ] **Step 4: Implement FastAPI app factory**

```python
# src/adaptive_rag/api/app.py
from fastapi import FastAPI

from adaptive_rag.api.routes.health import router as health_router
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Adaptive RAG", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
```

- [ ] **Step 5: Run API test**

Run:

```bash
uv run pytest tests/integration/api/test_health.py -q
```

Expected: `1 passed`.

- [ ] **Step 6: Run app import smoke test**

Run:

```bash
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
```

Expected output:

```txt
Adaptive RAG
```

- [ ] **Step 7: Commit**

```bash
git add src/adaptive_rag/api tests/integration/api
git commit -m "feat: add FastAPI health endpoint"
```

---

### Task 5: Typer CLI Shell

**Files:**
- Create: `src/adaptive_rag/cli/app.py`
- Create: `tests/integration/cli/test_cli.py`

- [ ] **Step 1: Write failing CLI tests**

```python
# tests/integration/cli/test_cli.py
from typer.testing import CliRunner

from adaptive_rag.cli.app import app


def test_cli_version_command():
    runner = CliRunner()

    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "adaptive-rag 0.1.0" in result.stdout


def test_cli_health_command():
    runner = CliRunner()

    result = runner.invoke(app, ["health"])

    assert result.exit_code == 0
    assert "ok" in result.stdout
```

- [ ] **Step 2: Run CLI tests to verify failure**

Run:

```bash
uv run pytest tests/integration/cli/test_cli.py -q
```

Expected: FAIL with `ModuleNotFoundError` for `adaptive_rag.cli.app`.

- [ ] **Step 3: Implement CLI app**

```python
# src/adaptive_rag/cli/app.py
import typer
from rich.console import Console

from adaptive_rag import __version__
from adaptive_rag.config.logging import configure_logging
from adaptive_rag.config.settings import get_settings

app = typer.Typer(no_args_is_help=True)
console = Console()


@app.callback()
def callback() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def version() -> None:
    console.print(f"adaptive-rag {__version__}")


@app.command()
def health() -> None:
    console.print("ok")


def main() -> None:
    app()
```

- [ ] **Step 4: Run CLI tests**

Run:

```bash
uv run pytest tests/integration/cli/test_cli.py -q
```

Expected: `2 passed`.

- [ ] **Step 5: Run installed CLI command**

Run:

```bash
uv run adaptive-rag version
```

Expected output includes:

```txt
adaptive-rag 0.1.0
```

- [ ] **Step 6: Commit**

```bash
git add src/adaptive_rag/cli tests/integration/cli
git commit -m "feat: add Typer CLI shell"
```

---

### Task 6: Quality Gate

**Files:**
- Modify only if tools report concrete errors in files created by this milestone.

- [ ] **Step 1: Run all tests**

Run:

```bash
uv run pytest
```

Expected: all tests pass.

- [ ] **Step 2: Run Ruff**

Run:

```bash
uv run ruff check .
```

Expected: command exits with code `0`.

- [ ] **Step 3: Run mypy**

Run:

```bash
uv run mypy src
```

Expected: command exits with code `0`.

- [ ] **Step 4: Run import smoke tests**

Run:

```bash
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
uv run adaptive-rag health
```

Expected output includes:

```txt
Adaptive RAG
ok
```

- [ ] **Step 5: Commit fixes if any quality-gate changes were required**

If no changes were required, do not create an empty commit.

If changes were required, run:

```bash
git add src tests pyproject.toml alembic.ini alembic README.md .env.example .gitignore
git commit -m "chore: pass foundation quality gates"
```

---

## Completion Criteria

Milestone 1 is complete when:

- `uv sync --extra dev` succeeds.
- `uv run pytest` passes.
- `uv run ruff check .` passes.
- `uv run mypy src` passes.
- `uv run adaptive-rag version` prints `adaptive-rag 0.1.0`.
- `uv run python -c "from adaptive_rag.api.app import app; print(app.title)"` prints `Adaptive RAG`.
- The repo has commits for package scaffold, settings, DB foundation, API health, and CLI shell.

## Next Plan

The next implementation plan should be Milestone 2: domain models, SQLAlchemy tables, Alembic migration for projects/sources/documents/chunks/jobs/audit/evals, and repository tests for project isolation.
