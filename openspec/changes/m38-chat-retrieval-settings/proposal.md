# Propuesta M38 de chat retrieval settings

## Contexto

El chat usa `RetrievalService` como tool compartida y hoy recibe
`retrieval_limit` desde la request. `rerank` ya existe en la superficie de
retrieval, en runtime settings como slot fijo y en audit/history, pero las
respuestas de chat no resuelven una politica efectiva de rerank ni limites
desde settings globales/proyecto.

M37 dejo proyectos compartidos, sesiones privadas y runtime settings por
proyecto. El siguiente incremento debe hacer que la calidad del contexto de
chat sea configurable de forma consistente con ese modelo: defaults globales
para nuevos proyectos y overrides por proyecto cuando un admin necesite pisar
el comportamiento.

## Objetivo

Agregar settings efectivos de retrieval para chat, heredados desde defaults
globales y overrideables por proyecto, para controlar:

- `retrieval_limit`;
- `rerank_enabled`;
- `rerank_candidate_limit`.

Los defaults iniciales son `retrieval_limit=5`, `rerank_enabled=true` y
`rerank_candidate_limit=10`. Los limites configurables no pueden superar `50`.

## Alcance

Incluye:

- Schema y repositories para global chat retrieval defaults y project overrides.
- API/CLI/runtime wiring para resolver settings efectivos en chat.
- Uso de rerank en respuestas de chat cuando el setting efectivo lo habilita.
- Validaciones de limites y candidate limit.
- Audit/history con strategy, rerank metadata, usage/cost y configuracion
  efectiva suficiente para depurar una respuesta.
- Tests y eval/smoke que midan `dense_sparse` vs chat con rerank efectivo.

No incluye:

- Promover otros retrieval strategies a default.
- Cambiar el contrato provider de Qwen rerank.
- Agregar un nuevo algoritmo de rerank o heuristica auto-rerank.
- Reentrenar embeddings, cambiar chunking o tocar graph retrieval.
