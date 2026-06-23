# Diseno M24 de ingestion ops surface

## Decisiones

M24 debe reutilizar `JobRepository` e `IngestionPipeline`. La surface publica no
debe crear una segunda cola ni saltarse los eventos existentes. Las operaciones
nuevas se modelan en un modulo compartido `adaptive_rag.ingestion_ops` para que
API y CLI tengan la misma semantica.

## API

M24 agrega endpoints project-scoped:

- `POST /projects/{project_id}/sources/{source_id}/ingestion-jobs`: encola un
  job `ingest_source` con payload `{"source_id": "<uuid>"}`.
- `GET /projects/{project_id}/ingestion-jobs`: lista jobs con filtros
  opcionales `status`, `source_id` y `job_type`.
- `GET /projects/{project_id}/ingestion-jobs/{job_id}`: devuelve job y eventos.
- `POST /projects/{project_id}/ingestion-jobs/{job_id}/retry`: reencola jobs
  `blocked` o `dead_letter`.
- `POST /projects/{project_id}/ingestion-jobs/run-next`: procesa un job
  disponible con `IngestionPipeline` para uso local.

## CLI

El grupo existente `adaptive-rag jobs` se extiende con:

- `enqueue-ingest-source --project-id --source-id`
- `list --project-id [--status] [--source-id]`
- `show --project-id --job-id`
- `retry --project-id --job-id`

`run-worker --once` sigue existiendo y debe reportar `blocked` cuando el pipeline
toma un job pero lo bloquea por error no retryable.

## Frontend

La vista `Authoring` agrega operaciones de ingestion sobre el project/source
seleccionado: enqueue por source, refresh de jobs, run next job y retry para
jobs `blocked` o `dead_letter`. La UI no debe afirmar que indexing/chunking ya
ocurrio; solo muestra document ingestion/job state.

## Errores

Los errores esperados deben ser estables:

- project faltante: `project not found`
- source faltante o cross-project: `source not found`
- job faltante o cross-project: `job not found`
- retry no permitido: `job is not retryable`

## Validacion

El PR debe cerrar con pytest, Ruff, mypy, Vitest, typecheck, lint, build,
OpenSpec strict y `git diff --check`.
