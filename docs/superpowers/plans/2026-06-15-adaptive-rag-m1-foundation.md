# Plan de implementación M1 Foundation de Adaptive RAG

> **Para workers agentic:** SUB-SKILL REQUERIDA: usar
> `superpowers:subagent-driven-development` (recomendado) o
> `superpowers:executing-plans` para implementar este plan tarea por tarea. Los
> pasos usan sintaxis de checkbox (`- [ ]`) para tracking.

**Objetivo:** crear la base del proyecto Python para Adaptive RAG: layout del
paquete, settings, logging, sesión de DB/base Alembic, endpoint de health en
FastAPI, shell CLI con Typer y quality gates.

**Arquitectura:** este hito crea solo infraestructura. API y CLI son
entrypoints delgados; la configuración compartida vive en `adaptive_rag.config`;
el código de conexión a base de datos vive en `adaptive_rag.db`; todavía no se
implementa comportamiento de RAG, providers, ingestion ni retrieval.

**Stack técnico:** Python 3.12, uv, FastAPI, Typer, Rich, Pydantic Settings,
Pydantic AI slim con soporte OpenAI-compatible, SQLAlchemy 2, Alembic, psycopg,
pytest, httpx, ruff y mypy.

---

## Alcance

Este plan cubre solo Milestone 1. Intencionalmente no implementa tablas de
dominio, ingestion jobs, LlamaIndex, integración Qwen, modelos pgvector,
retrieval, orquestación de chat ni evals. La dependencia `pydantic-ai-slim`
queda instalada como base del runtime de agente futuro, pero no se usa en código
productivo durante M1. Eso pertenece a planes posteriores.
Unstructured queda fuera de v1 y solo debe reaparecer como experimento
post-producción si los evals de parsing/retrieval lo justifican.

## Estructura objetivo de archivos

Archivos creados en este hito:

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

### Tarea 1: esqueleto del paquete del proyecto

**Estado:** completada en el commit `d2d23d4 chore: scaffold adaptive rag package`.

**Archivos:**
- Crear: `pyproject.toml`
- Crear: `.gitignore`
- Crear: `.env.example`
- Crear: `README.md`
- Crear: `src/adaptive_rag/__init__.py`
- Crear: archivos `__init__.py` de paquete bajo `api`, `api/routes`, `cli`,
  `config` y `db`

- [x] **Paso 1: crear `pyproject.toml`**

```toml
[project]
name = "adaptive-rag"
version = "0.1.0"
description = "Sistema RAG adaptativo personal y aislado por proyecto."
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.14",
  "fastapi>=0.115",
  "httpx>=0.28",
  "pgvector>=0.3",
  "psycopg[binary]>=3.2",
  "pydantic-ai-slim[openai]>=1.107.0",
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

- [x] **Paso 2: crear `.gitignore`**

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

- [x] **Paso 3: crear `.env.example`**

```dotenv
ADAPTIVE_RAG_ENV=local
ADAPTIVE_RAG_LOG_LEVEL=INFO
ADAPTIVE_RAG_DATABASE_URL=postgresql+psycopg://adaptive_rag:adaptive_rag@localhost:5432/adaptive_rag
ADAPTIVE_RAG_API_KEY=
ADAPTIVE_RAG_VECTOR_STORE=pgvector
```

- [x] **Paso 4: crear `README.md`**

````markdown
# Adaptive RAG

Sistema RAG personal, aislado por proyecto, pensado para aprendizaje y
portafolio.

## Desarrollo local

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
```
````

- [x] **Paso 5: crear archivos init de paquete**

```python
# src/adaptive_rag/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Crear archivos vacíos:

```txt
src/adaptive_rag/api/__init__.py
src/adaptive_rag/api/routes/__init__.py
src/adaptive_rag/cli/__init__.py
src/adaptive_rag/config/__init__.py
src/adaptive_rag/db/__init__.py
```

- [x] **Paso 6: sincronizar dependencias**

Ejecutar:

```bash
uv sync --extra dev
```

Resultado esperado: el comando termina con código `0` y crea `.venv`.

- [x] **Paso 7: verificar import del paquete**

Ejecutar:

```bash
uv run python -c "import adaptive_rag; print(adaptive_rag.__version__)"
```

Output esperado:

```txt
0.1.0
```

- [x] **Paso 8: commit**

```bash
git add pyproject.toml .gitignore .env.example README.md src/adaptive_rag
git commit -m "chore: scaffold adaptive rag package"
```

---

### Tarea 2: settings y logging

**Archivos:**
- Crear: `src/adaptive_rag/config/settings.py`
- Crear: `src/adaptive_rag/config/logging.py`
- Crear: `tests/unit/config/test_settings.py`

- [ ] **Paso 1: escribir tests de settings que fallen**

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

- [ ] **Paso 2: correr tests para verificar el fallo**

Ejecutar:

```bash
uv run pytest tests/unit/config/test_settings.py -q
```

Resultado esperado: FAIL con `ModuleNotFoundError` para
`adaptive_rag.config.settings`.

- [ ] **Paso 3: implementar settings**

```python
# src/adaptive_rag/config/settings.py
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


VectorStoreName = Literal["pgvector"]


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

- [ ] **Paso 4: implementar configuración de logging**

```python
# src/adaptive_rag/config/logging.py
import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
```

- [ ] **Paso 5: correr tests de settings**

Ejecutar:

```bash
uv run pytest tests/unit/config/test_settings.py -q
```

Resultado esperado: `2 passed`.

- [ ] **Paso 6: correr lint del paquete de config**

Ejecutar:

```bash
uv run ruff check src/adaptive_rag/config tests/unit/config
```

Resultado esperado: el comando termina con código `0`.

- [ ] **Paso 7: commit**

```bash
git add src/adaptive_rag/config tests/unit/config
git commit -m "feat: add application settings"
```

---

### Tarea 3: sesión de database y base Alembic

**Archivos:**
- Crear: `src/adaptive_rag/db/base.py`
- Crear: `src/adaptive_rag/db/session.py`
- Crear: `tests/unit/db/test_session.py`
- Crear: `alembic.ini`
- Crear: `alembic/env.py`
- Crear: `alembic/versions/.gitkeep`

- [ ] **Paso 1: escribir tests de sesión DB que fallen**

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

- [ ] **Paso 2: correr tests para verificar el fallo**

Ejecutar:

```bash
uv run pytest tests/unit/db/test_session.py -q
```

Resultado esperado: FAIL con `ModuleNotFoundError` para `adaptive_rag.db.base`
o `adaptive_rag.db.session`.

- [ ] **Paso 3: implementar base SQLAlchemy**

```python
# src/adaptive_rag/db/base.py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Paso 4: implementar helpers de sesión DB**

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

- [ ] **Paso 5: crear config de Alembic**

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

- [ ] **Paso 6: crear env de Alembic**

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

- [ ] **Paso 7: mantener el directorio de versiones de Alembic**

Crear archivo vacío:

```txt
alembic/versions/.gitkeep
```

- [ ] **Paso 8: correr tests DB**

Ejecutar:

```bash
uv run pytest tests/unit/db/test_session.py -q
```

Resultado esperado: `2 passed`.

- [ ] **Paso 9: correr syntax check de Alembic**

Ejecutar:

```bash
uv run python -m py_compile alembic/env.py
```

Resultado esperado: el comando termina con código `0`.

- [ ] **Paso 10: commit**

```bash
git add src/adaptive_rag/db tests/unit/db alembic.ini alembic
git commit -m "feat: add database session foundation"
```

---

### Tarea 4: endpoint de health en FastAPI

**Archivos:**
- Crear: `src/adaptive_rag/api/app.py`
- Crear: `src/adaptive_rag/api/routes/health.py`
- Crear: `tests/integration/api/test_health.py`

- [ ] **Paso 1: escribir test de API que falle**

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

- [ ] **Paso 2: correr test de API para verificar el fallo**

Ejecutar:

```bash
uv run pytest tests/integration/api/test_health.py -q
```

Resultado esperado: FAIL con `ModuleNotFoundError` para `adaptive_rag.api.app`.

- [ ] **Paso 3: implementar ruta de health**

```python
# src/adaptive_rag/api/routes/health.py
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "adaptive-rag"}
```

- [ ] **Paso 4: implementar app factory de FastAPI**

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

- [ ] **Paso 5: correr test de API**

Ejecutar:

```bash
uv run pytest tests/integration/api/test_health.py -q
```

Resultado esperado: `1 passed`.

- [ ] **Paso 6: correr smoke test de import de la app**

Ejecutar:

```bash
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
```

Output esperado:

```txt
Adaptive RAG
```

- [ ] **Paso 7: commit**

```bash
git add src/adaptive_rag/api tests/integration/api
git commit -m "feat: add FastAPI health endpoint"
```

---

### Tarea 5: shell CLI con Typer

**Archivos:**
- Crear: `src/adaptive_rag/cli/app.py`
- Crear: `tests/integration/cli/test_cli.py`

- [ ] **Paso 1: escribir tests de CLI que fallen**

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

- [ ] **Paso 2: correr tests de CLI para verificar el fallo**

Ejecutar:

```bash
uv run pytest tests/integration/cli/test_cli.py -q
```

Resultado esperado: FAIL con `ModuleNotFoundError` para `adaptive_rag.cli.app`.

- [ ] **Paso 3: implementar app CLI**

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

- [ ] **Paso 4: correr tests de CLI**

Ejecutar:

```bash
uv run pytest tests/integration/cli/test_cli.py -q
```

Resultado esperado: `2 passed`.

- [ ] **Paso 5: correr comando CLI instalado**

Ejecutar:

```bash
uv run adaptive-rag version
```

El output esperado incluye:

```txt
adaptive-rag 0.1.0
```

- [ ] **Paso 6: commit**

```bash
git add src/adaptive_rag/cli tests/integration/cli
git commit -m "feat: add Typer CLI shell"
```

---

### Tarea 6: quality gate

**Archivos:**
- Modificar solo si las tools reportan errores concretos en archivos creados
  por este hito.

- [ ] **Paso 1: correr todos los tests**

Ejecutar:

```bash
uv run pytest
```

Resultado esperado: todos los tests pasan.

- [ ] **Paso 2: correr Ruff**

Ejecutar:

```bash
uv run ruff check .
```

Resultado esperado: el comando termina con código `0`.

- [ ] **Paso 3: correr mypy**

Ejecutar:

```bash
uv run mypy src
```

Resultado esperado: el comando termina con código `0`.

- [ ] **Paso 4: correr smoke tests de import**

Ejecutar:

```bash
uv run python -c "from adaptive_rag.api.app import app; print(app.title)"
uv run adaptive-rag health
```

El output esperado incluye:

```txt
Adaptive RAG
ok
```

- [ ] **Paso 5: commitear fixes si el quality gate requirió cambios**

Si no se requieren cambios, no crear un commit vacío.

Si se requieren cambios, ejecutar:

```bash
git add src tests pyproject.toml alembic.ini alembic README.md .env.example .gitignore
git commit -m "chore: pass foundation quality gates"
```

---

## Criterios de completitud

Milestone 1 está completo cuando:

- `uv sync --extra dev` funciona correctamente.
- `uv run pytest` pasa.
- `uv run ruff check .` pasa.
- `uv run mypy src` pasa.
- `uv run adaptive-rag version` imprime `adaptive-rag 0.1.0`.
- `uv run python -c "from adaptive_rag.api.app import app; print(app.title)"`
  imprime `Adaptive RAG`.
- El repo tiene commits para package scaffold, settings, base DB, health API y
  shell CLI.

## Siguiente plan

El siguiente plan de implementación debe ser Milestone 2: modelos de dominio,
tablas SQLAlchemy, migración Alembic para projects/sources/documents/chunks/jobs
/audit/evals, columnas tipadas para metadata filtering y tests de repository
para aislamiento por proyecto más filtros por `source_id`, `document_id`,
`source_type`, `tags` y fechas. El schema de chunks debe incluir campos de
chunking semántico (`section_path`, `heading`, `char_start`, `char_end`,
`token_count`, `prev_chunk_id`, `next_chunk_id`, `chunker_version`,
`chunker_config_hash`) y campos de Contextual Retrieval (`contextual_text`,
`embedding_input_text`, `lexical_input_text`, metadata del contextualizer e
`index_fingerprint`), aunque la generación Qwen del contexto se implemente en un
hito posterior. M2 también debe incluir fixtures de Markdown con headings,
listas, tablas, code fences, párrafos largos y documentos cortos para probar que
el chunker no corta estructuras de forma errónea ni pierde contenido.
