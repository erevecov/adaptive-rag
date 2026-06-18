# Tareas M2 de repositories

## 1. Planificacion y setup

- [x] 1.1 Crear branch `codex/m2-repositories` desde el `origin/main` actual.
- [x] 1.2 Ejecutar `uv sync --extra dev`, `uv run pytest`, `uv run ruff check .` y `uv run mypy src` para confirmar baseline.
- [x] 1.3 Consultar docs actuales de SQLAlchemy 2.x con Context7 para confirmar el estilo `select()`/`Session.scalars()`.

## 2. Contrato OpenSpec

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para `m2-repositories`.
- [x] 2.2 Validar `openspec validate m2-repositories --strict`.

## 3. Tests TDD de repositories

- [x] 3.1 Agregar tests rojos para crear y obtener proyectos.
- [x] 3.2 Agregar tests rojos para sources con aislamiento por `project_id` y filtros tipados.
- [x] 3.3 Agregar tests rojos para documents y document versions.
- [x] 3.4 Agregar tests rojos para chunks ordenados por document version.

## 4. Implementacion

- [x] 4.1 Crear `src/adaptive_rag/db/repositories/`.
- [x] 4.2 Implementar filtros tipados y repositories sincronicos.
- [x] 4.3 Exportar la API publica de repositories.
- [x] 4.4 Confirmar que los repositories no hacen `commit()`.

## 5. Quality gate y handoff

- [x] 5.1 Ejecutar `uv run pytest`.
- [x] 5.2 Ejecutar `uv run ruff check .`.
- [x] 5.3 Ejecutar `uv run mypy src`.
- [x] 5.4 Ejecutar `openspec validate --specs --strict`.
- [x] 5.5 Actualizar `docs/progress.md` con el estado de `m2-repositories`.
