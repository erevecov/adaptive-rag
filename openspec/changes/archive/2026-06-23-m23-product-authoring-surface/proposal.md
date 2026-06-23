# Propuesta M23 de product authoring surface

## Why

M22 redefinio v1 como producto local-first single-user terminado. La primera
brecha de producto es que el usuario todavia no puede crear un proyecto ni
agregar sus propias sources desde superficies publicas. El core ya tiene tablas
`projects` y `sources`, repositories, retrieval/chat por `project_id` e ingestion
para jobs `ingest_source`, pero el happy path aun depende de fixtures internas,
tests o SQL manual.

M23 debe convertir ese modelo existente en una superficie publica minima de
authoring. Sin esto no se puede cerrar onboarding real, ingestion operativa ni
demo final con datos propios.

## What Changes

- Crear el change OpenSpec `m23-product-authoring-surface`.
- Agregar la capability `product-authoring-surface`.
- Declarar contratos para crear/listar/ver projects y sources por API, CLI y
  frontend.
- Mantener ingestion execution, job-state UI, retry/dead-letter y runbook final
  fuera de M23; eso queda para M24/M25.
- Actualizar progress, roadmap y arquitectura con M23 activo.

## Capacidades

### Capacidades nuevas

- `product-authoring-surface`

### Capacidades modificadas

- `v1-product-completion`
- `domain-schema`
- `repositories`
- `chat-frontend`

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- No cambia codigo productivo en este PR de planificacion.
- No agrega migraciones obligatorias en el plan inicial; M23 debe preferir los
  campos existentes salvo que una implementacion demuestre una brecha real.
- No encola ingestion jobs ni procesa documentos desde la nueva authoring
  surface; crear la source solo persiste identidad y metadata publica.
- No cambia dense retrieval como default, rerank opt-in, graph opt-in,
  provider runtime, auth, voice, MCP, PDF/Office ni retrieval experimental.
