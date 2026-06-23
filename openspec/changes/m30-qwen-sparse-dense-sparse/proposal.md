# Proposal M30 Qwen sparse dense_sparse

## Why

M29 added local lexical retrieval and dense+lexical RRF. The next backend
contract needed before frontend polish is Qwen sparse retrieval: a provider
adapter, sparse backfill/reindex path, and an opt-in `dense_sparse` retrieval
strategy that can be measured in M31.

Current DashScope docs confirm `text-embedding-v3` and `text-embedding-v4`
support `output_type=sparse` and `output_type=dense&sparse`, with
`sparse_embedding` entries carrying `index`, `value` and `token`. This is
enough to implement the provider contract without guessing payload shape.

## What Changes

- Add a sparse embedding provider contract plus Qwen/DashScope and fake
  implementations.
- Add a sparse embedding pipeline/backfill command that fills the existing
  `chunk_sparse_embeddings` table from contextualized chunk input.
- Add sparse retrieval over stored sparse rows and expose
  `strategy=dense_sparse` as an opt-in dense+sparse RRF strategy.
- Add API, CLI and offline eval strategy selection coverage.
- Extend audit trail with nullable `sparse_score` while preserving existing
  dense, lexical, RRF and rerank score columns.
- Archive M29 and update roadmap/progress docs to make M30 active.

## Non-Goals

- Promoting sparse retrieval to default.
- Frontend controls for sparse retrieval.
- Adding a sparse vector extension or ANN sparse index in this slice.
- Replacing lexical/RRF or rerank.
- Running hosted sparse evals by default.

## Validation

- Unit tests for Qwen sparse payload parsing, sparse pipeline idempotency,
  sparse retrieval scoring and `dense_sparse` RRF.
- API/CLI/eval tests for `strategy=dense_sparse`.
- Migration/model/repository tests for `sparse_score`.
- Full Python checks and OpenSpec validation.
