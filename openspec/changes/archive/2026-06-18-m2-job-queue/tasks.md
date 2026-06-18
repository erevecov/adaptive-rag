# Tareas M2 de job queue

## 1. Planificacion y setup

- [x] 1.1 Confirmar merge de `m2-repositories` en `origin/main`.
- [x] 1.2 Crear branch `codex/m2-job-queue` desde el `origin/main` actual.
- [x] 1.3 Ejecutar baseline: `uv run pytest`, `uv run ruff check .`, `uv run mypy src`, `openspec validate --specs --strict`.
- [x] 1.4 Consultar docs actuales de Alembic con Context7 para migraciones.

## 2. Contrato OpenSpec

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para `m2-job-queue`.
- [x] 2.2 Validar `openspec validate m2-job-queue --strict`.

## 3. Tests TDD

- [x] 3.1 Agregar tests rojos para modelos `Job` y `JobEvent`.
- [x] 3.2 Agregar tests rojos para migracion Alembic de jobs/events.
- [x] 3.3 Agregar tests rojos para `JobRepository.create()` y eventos.
- [x] 3.4 Agregar tests rojos para leasing, completion, retry, blocked, dead-letter y leases vencidos.

## 4. Implementacion

- [x] 4.1 Agregar modelos SQLAlchemy `Job` y `JobEvent`.
- [x] 4.2 Agregar migracion Alembic `m2_job_queue`.
- [x] 4.3 Implementar `JobRepository`.
- [x] 4.4 Exportar modelos y repository en APIs publicas.

## 5. Quality gate y handoff

- [x] 5.1 Ejecutar `uv run pytest`.
- [x] 5.2 Ejecutar `uv run ruff check .`.
- [x] 5.3 Ejecutar `uv run mypy src`.
- [x] 5.4 Ejecutar `openspec validate --specs --strict`.
- [x] 5.5 Archivar `m2-job-queue` y actualizar docs de progreso.
