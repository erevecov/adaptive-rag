# Propuesta M24 de ingestion ops surface

## Why

M23 permite crear projects y sources desde superficies publicas, pero el usuario
todavia no puede convertir esos sources en documents ni operar el estado de
ingestion sin conocer internals de SQL o jobs. Para que v1 sea un producto real,
el flujo local debe incluir una operacion explicita de ingestion, estado de jobs,
errores visibles y retry/dead-letter recovery.

## What Changes

- Crear el change OpenSpec `m24-ingestion-ops-surface`.
- Agregar una surface publica para encolar jobs `ingest_source` por source.
- Exponer listado/detalle de jobs y eventos por proyecto.
- Exponer retry manual para jobs `blocked` o `dead_letter`.
- Exponer una operacion local `run-next` que procesa un job `ingest_source`
  usando el pipeline existente.
- Extender CLI y frontend con controles compactos para enqueue/run/status.
- Mantener chunking, embeddings, search reindex y providers fuera de M24.

## Fuera de alcance

- No agrega edicion de sources.
- No agrega chunking/embeddings despues de `document_versions`.
- No cambia defaults de retrieval, rerank, graph o providers.
- No agrega workers background administrados por la UI.
- No agrega auth multi-user ni permisos.

## Impacto

El producto puede completar el tramo authoring -> ingestion de documents desde
superficies publicas. M25 queda libre para onboarding/runbook y demo local con
datos propios sobre esta base.
