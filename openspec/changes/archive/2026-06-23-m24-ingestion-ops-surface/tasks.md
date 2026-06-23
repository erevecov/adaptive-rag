# Tareas M24 de ingestion ops surface

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #118 esta mergeado en `origin/main`.
- [x] 1.2 Crear branch `codex/m24-ingestion-ops-surface` desde `origin/main`.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M23.
- [x] 1.4 Revisar `JobRepository`, `IngestionPipeline`, API, CLI y frontend
  authoring existentes.

## 2. Change OpenSpec

- [x] 2.1 Agregar propuesta, diseno y tasks de
  `m24-ingestion-ops-surface`.
- [x] 2.2 Agregar capability nueva `ingestion-ops-surface`.
- [x] 2.3 Agregar deltas para `job-queue`, `ingestion-pipeline`,
  `chat-frontend`, `repositories` y `v1-product-completion`.

## 3. Implementacion backend/API

- [x] 3.1 Agregar tests rojos de repository/ops para list/retry de jobs.
- [x] 3.2 Implementar `JobRepository.list()` y `requeue()`.
- [x] 3.3 Agregar modulo compartido `adaptive_rag.ingestion_ops`.
- [x] 3.4 Agregar schemas/routes HTTP de ingestion ops.
- [x] 3.5 Mejorar `IngestionPipeline.run_next()` para reportar jobs blocked.
- [x] 3.6 Confirmar tests backend/API.

## 4. Implementacion CLI

- [x] 4.1 Agregar tests rojos para `jobs enqueue-ingest-source|list|show|retry`.
- [x] 4.2 Implementar comandos CLI usando `ingestion_ops`.
- [x] 4.3 Confirmar que `run-worker --once` reporta `processed`, `blocked` o
  `idle` de forma estable.

## 5. Implementacion frontend

- [x] 5.1 Agregar tests rojos de `apiClient` para ingestion ops.
- [x] 5.2 Implementar tipos y metodos frontend de ingestion jobs.
- [x] 5.3 Agregar controles compactos de enqueue/run/status/retry en Authoring.
- [x] 5.4 Confirmar tests frontend.

## 6. Quality gate y archive

- [x] 6.1 Validar backend con pytest, Ruff y mypy.
- [x] 6.2 Validar frontend con Vitest, typecheck, lint y build.
- [x] 6.3 Validar OpenSpec activo y specs canonicas.
- [x] 6.4 Archivar `m24-ingestion-ops-surface`.
- [x] 6.5 Actualizar `docs/progress.md` y `docs/roadmap.md` hacia M25.
