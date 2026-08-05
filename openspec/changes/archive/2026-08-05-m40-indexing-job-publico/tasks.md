# Tareas M40 de indexing job publico

## 1. Planificacion y OpenSpec

- [x] 1.1 Inventariar worker, first_run, acceptance, quality-gate y gap de indexing.
- [x] 1.2 Escribir proposal/design/tasks + deltas de specs.
- [x] 1.3 Validar change con `openspec change validate m40-indexing-job-publico --strict`.

## 2. Tests rojos

- [x] 2.1 Unit: ingest exitoso encola `index_document_version` sin crear chunks.
- [x] 2.2 Unit: indexing job produce chunks + contextual + dense/sparse embeddings.
- [x] 2.3 Unit/integration: run_next procesa ambos job types; idle cuando no hay mas.
- [x] 2.4 Integration: first-run / public path source→worker→chunks→chat citations
  sin llamar pipelines de indexing inline.
- [x] 2.5 Structural: first_run/acceptance no importan ChunkingPipeline para el path
  feliz (usan job path).

## 3. Implementacion

- [x] 3.1 `IndexingPipeline` + constantes de job type.
- [x] 3.2 Encolar index job al completar `ingest_source`.
- [x] 3.3 Extender `JobRepository.lease_next` / worker / `ingestion_ops.run_next`
  para family de jobs.
- [x] 3.4 Redirigir first_run y acceptance al drain de jobs.
- [x] 3.5 Actualizar reportes (counts) desde resultados de indexing job / DB.

## 4. Gates y cierre

- [x] 4.1 `uv run ruff check .` + `uv run mypy src` + pytest del area y full si viable.
- [x] 4.2 E2E evidence en scratch + body de PR.
- [x] 4.3 Actualizar `docs/progress.md` y `docs/roadmap.md`.
- [x] 4.4 Archivar OpenSpec change y abrir PR.
