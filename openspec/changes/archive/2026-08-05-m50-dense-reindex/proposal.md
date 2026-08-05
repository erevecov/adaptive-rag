# Propuesta M50 — Dense reindex + contextualizacion LLM opt-in

## Why

Tras cambios de modelo/parser o corpus, el operador necesita re-embed denso
por proyecto con reporte JSON y watermark, y poder optar por un contextualizer
LLM distinto del deterministico con A/B medible.

## What Changes

- CLI `adaptive-rag dense reindex --project-id` (opcional version) con force,
  JSON report y watermark ISO.
- `DenseEmbeddingPipeline` soporta `force=True` para re-embed.
- Contextualizer `llm_opt_in` + CLI `contextualize reindex` / `ab-compare`.
- `ContextualizationPipeline` soporta `force=True`.
- OpenSpec deltas y tests.

## Fuera de alcance

- Hosted LLM obligatorio (opt-in local/fake label suficiente para A/B).
- Sparse reindex (puede reutilizar dense path pattern luego).
- Tag v1.0.

## Impacto

Operadores re-indexan dense con evidencia JSON y pueden comparar summaries
deterministic vs opt-in LLM-labeled sin salir del stack local.
