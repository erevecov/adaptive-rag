# Propuesta M3 de ingestion y retrieval

## Why

M2 cerro los contratos persistentes: schema de dominio, repositories, job queue
y politica segura de fetch de URLs. El siguiente riesgo es que ingestion,
chunking, embeddings y retrieval se implementen mezclados en un PR grande, lo
que haria mas dificil revisar correctness, aislamiento por proyecto, offsets de
citas y errores de providers.

M3 necesita un plan OpenSpec activo que divida el trabajo en slices revisables
antes de escribir codigo nuevo.

## What Changes

- Crear el change OpenSpec `m3-ingestion-retrieval-plan`.
- Fijar la secuencia inicial de M3 en slices secuenciales:
  `m3-ingestion-pipeline`, `m3-chunking-baseline`,
  `m3-embedding-baseline`, `m3-retrieval-baseline` y
  `m3-quality-gate`.
- Declarar que ingestion empieza con fakes/determinismo y sin llamadas live a
  providers.
- Separar parsing, chunking, embeddings y retrieval para reducir conflictos y
  hacer cada PR verificable por contrato.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar el change
  activo y el siguiente slice recomendado.

No se implementan todavia workers productivos, parsers, chunkers, embeddings,
retrieval API/CLI, rerank, chat ni evals.

## Capacidades

### Capacidades nuevas

- `ingestion-retrieval-plan`

### Capacidades modificadas

- Ninguna. Las specs canonicas de M2 quedan como dependencias.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo.
- No requiere credenciales de providers.

