# Propuesta M40 de indexing job publico

## Why

Hoy el worker publico solo convierte sources en `document_versions`. El camino
que llega a chunks, contextual summaries y embeddings densos/sparse es inline
privilegiado dentro de first-run, acceptance y quality-gate. Eso deja el
producto real (API/CLI/UI + worker) sin indexing observable y rompe el contrato
de un solo path de producto.

## What Changes

- Introducir job publico `index_document_version` que ejecuta chunking →
  contextualizacion → dense/sparse embeddings.
- Encadenar ese job tras un `ingest_source` exitoso (misma source/document
  version), con eventos y estados visibles en worker y API de ingestion ops.
- Hacer que first-run, acceptance y quality-gate usen el mismo worker/job path
  (sin pipelines de indexing inline privilegiados).
- Ampliar `run-next` / `run-worker` para procesar ambos job types del family
  de ingestion/indexing.
- Tests de integracion: source publica → worker → chunks/embeddings → chat
  con citations.

## Fuera de alcance

- PDF/DOCX (M45).
- Lease recovery / fail() callers (M41).
- Chat multi-turn (M42).
- Lifecycle PATCH/DELETE authoring (M43).
- CI GitHub Actions / compose frontend (M44).
- Reindex masivo / contextualizacion LLM opt-in (M50).

## Impacto

El usuario local puede authoring → enqueue → worker y obtener un corpus
recuperable y citable. Los gates de release dejan de usar un atajo privilegiado
y validan el mismo camino de producto.
