# Design M30 Qwen sparse dense_sparse

## Provider Contract

Add a sparse embedding contract separate from `DenseEmbeddingProvider`:

- `SparseEmbeddingProvider.embed_documents(texts)` for stored chunks.
- `SparseEmbeddingProvider.embed_query(text)` for query-time retrieval.
- Each result contains sorted indices, values and optional tokens.

`FakeSparseEmbeddingProvider` stays deterministic and local. Qwen uses the
existing `QwenHTTPEmbeddingClient` transport/budget/usage path and adds a
DashScope native request with:

- `model=text-embedding-v4` by default.
- `input.texts=[...]`.
- `parameters.output_type=sparse`.
- `parameters.text_type=document|query`.
- optional `parameters.dimension=1024` only for parity with dense settings.

OpenAI-compatible embedding endpoints are not used for sparse because the
provider docs expose `output_type` on the DashScope API.

## Storage and Backfill

The schema already has `chunk_sparse_embeddings`. M30 adds a repository and
pipeline that:

- Builds the same contextualized input as dense embeddings.
- Computes an input hash and provider/model fingerprint.
- Reuses current rows when fingerprint and input hash match.
- Replaces stale sparse rows for the chunk before inserting the current row.
- Leaves transaction control to the caller.

The first operational surface is CLI-only:
`adaptive-rag sparse backfill --project-id <id>`.

## Retrieval

Add `SparseRetriever` that loads filtered sparse rows, scores dot-product
over overlapping indices, preserves original citations and returns metadata
with sparse rank/score/fingerprint. The first implementation scores in Python
after SQL filters; this is acceptable for an opt-in M30 contract and avoids a
new sparse database extension before M31 evidence.

`RetrievalService` accepts `strategy=dense_sparse`. It runs dense retrieval and
sparse retrieval, deduplicates by chunk id and applies the same RRF constant as
M29 (`k=60`). Results include `retrieval_metadata` with dense/sparse ranks,
scores, source strategies and RRF score.

## Surfaces

API, CLI and offline evals accept `dense_sparse` exactly like existing
strategies. The default remains `dense` everywhere. Chat keeps its default
dense retrieval path, but if future callers provide `dense_sparse` results the
audit trail records the strategy and score metadata.

## Audit

Add nullable `sparse_score` to `retrieved_chunks` and thread it through the
repository and SQLAlchemy audit writer. No existing rows need backfill.

## Risks

- Sparse provider docs may evolve. Mitigation: keep parser strict and tests
  cover the documented shape.
- Python scoring is not production-scale. Mitigation: M31 decides whether to
  optimize after quality evidence.
- Sparse rows can drift from chunk input. Mitigation: provider/model/input
  fingerprint drives idempotency and replacement.
