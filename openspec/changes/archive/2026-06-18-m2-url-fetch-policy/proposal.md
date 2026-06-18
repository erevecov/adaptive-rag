# Propuesta M2 de URL fetch policy

## Why

Adaptive RAG ya tiene schema, repositories y job queue, pero ingestion todavia no debe descargar URLs sin una politica explicita. Antes de conectar workers de ingestion, el sistema necesita bloquear SSRF, DNS rebinding via redirects, content types no permitidos y respuestas demasiado grandes.

## What Changes

- Agregar un modulo de policy/fetch seguro bajo `adaptive_rag.ingestion`.
- Validar que solo se acepten URLs `http` y `https` sin credenciales embebidas.
- Resolver DNS antes de cada request y redirect, bloqueando IPs no globales.
- Seguir redirects manualmente para validar cada destino antes de hacer request.
- Rechazar content types fuera de allowlist y respuestas sobre `max_response_bytes`.

No se implementan workers, ingestion pipeline, parsing con `trafilatura`, persistencia de documents ni scheduling.

## Capacidades

### Capacidades nuevas

- `url-fetch-policy`

### Capacidades modificadas

- Ninguna. `job-queue` queda como dependencia canonica ya archivada.

## Impacto

- Agregara codigo bajo `src/adaptive_rag/ingestion/`.
- Agregara tests unitarios de policy y fetch seguro.
- No agregara migraciones Alembic.

