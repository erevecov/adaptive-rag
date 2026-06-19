# Propuesta M4 de superficie de retrieval

## Why

M3 cerro el baseline persistente de ingestion, chunking, embeddings y dense
retrieval exacto, pero todavia no existe una superficie de producto para
consultar ese baseline desde API o CLI. El siguiente riesgo es saltar directo a
chat/tool calling, rerank o providers live sin antes fijar el contrato pequeno
que expone retrieval con filtros y citations.

M4 debe abrir una superficie minima y determinista de retrieval sobre datos ya
indexados, usando fakes o inyeccion de provider para query embeddings. Esto deja
un camino verificable hacia chat posterior sin mezclar orquestacion agentic,
lexical retrieval, sparse retrieval o Qwen live en el primer PR.

## What Changes

- Crear el change OpenSpec `m4-retrieval-surface-plan`.
- Definir una secuencia M4 que entregue:
  `m4-retrieval-service-contract`, `m4-retrieval-api-endpoint`,
  `m4-retrieval-cli-command` y `m4-quality-gate`.
- Fijar que la primera superficie usa query text mas provider inyectado/fake
  para producir el query embedding antes de llamar a `DenseRetriever`.
- Exigir paridad de filtros entre API y CLI para los filtros tipados ya
  soportados por M3.
- Mantener chat/tool calling, lexical full-text, sparse retrieval, RRF, rerank,
  evals y providers live fuera de este primer milestone.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar el change
  activo y el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- `retrieval-surface`

### Capacidades modificadas

- Ninguna. Las specs canonicas de M3 quedan como dependencias.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo.
- No requiere credenciales de providers live.
