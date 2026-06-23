# M29 Lexical Retrieval and RRF Design

## Decision

Implement M29 as an opt-in backend contract slice. Add `strategy=lexical` and
`strategy=hybrid_rrf` to the existing retrieval surface, keep `dense` as the
default, and expose the strategies through API, CLI and offline retrieval evals.

## Architecture

`LexicalRetriever` lives beside `DenseRetriever` and returns normal citable
results. It builds lexical input from existing fields: `contextual_summary`
when present plus the original chunk text. PostgreSQL uses full-text functions;
SQLite and unit tests use deterministic token overlap.

`RetrievalService` chooses the branch from `RetrievalStrategy`. Dense and graph
stay as-is. Lexical skips query embedding. Hybrid runs dense and lexical
candidate lists, deduplicates by chunk id and applies reciprocal rank fusion
with a fixed `k=60`.

## Interfaces

- API/CLI: extend existing `strategy` to `dense`, `graph`, `lexical`,
  `hybrid_rrf`.
- Evals: add `--retrieval-strategy` for offline retrieval cases.
- Payloads: add optional `retrieval_metadata` with dense/lexical/RRF score and
  rank fields.
- Audit: store score metadata into existing `dense_score`, `lexical_score` and
  `rrf_score` columns when available.

## Non-Goals

- No default promotion.
- No frontend changes.
- No Qwen sparse or provider-specific sparse payloads.
- No migrations or materialized lexical index in this slice.
