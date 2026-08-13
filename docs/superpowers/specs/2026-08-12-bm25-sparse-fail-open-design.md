# Design: BM25 base with sparse fail-open fallback

Date: 2026-08-12  
Status: approved  
Repo: adaptive-rag

## Problem

Chat and retrieval default to `dense_sparse`. If the sparse embedding
provider/model is missing or fails at query time, retrieval fails hard.
Okapi BM25 already exists as an opt-in strategy (`bm25`) but is not used as
the automatic lexical leg when neural sparse is unavailable.

## Goals

1. Keep **dense + neural sparse (RRF)** when sparse runtime is configured and
   succeeds.
2. Use **Okapi BM25** as the automatic substitute for the sparse leg when
   sparse is not configured or fails (provider, credentials, embed, retrieval
   errors).
3. Apply fail-open to **every** strategy that touches sparse: `sparse` and
   `dense_sparse` (chat, API, CLI, evals via `RetrievalService`).
4. Surface a clear `fallback_reason` for observability/audit.

## Non-goals

- Changing ingest `embedding_mode` (`dense` vs `dense_sparse` indexing).
- Changing explicit strategies `bm25`, `lexical`, `hybrid_rrf`, `dense`,
  `graph` (except that `sparse` / `dense_sparse` may report BM25 results after
  fallback).
- Three-way RRF (dense + sparse + BM25) when sparse succeeds.
- Building a persisted BM25 index / inverted index; keep the current in-memory
  Okapi scorer over candidate chunks.

## Decisions (locked)

| Topic | Choice |
|-------|--------|
| Happy path | Dense + sparse neural RRF when sparse works |
| Sparse availability | Runtime/slot sparse configured (provider + model + credentials) |
| Scope | Fail-open for `sparse` and `dense_sparse` everywhere they run through `RetrievalService` |
| Implementation locus | Inside `RetrievalService.search` (approach A) |

## Behavior

### Availability check

Sparse is “configured” when the sparse provider factory can build a live
sparse provider for the workspace (same resolution path as today:
persisted `sparse_embedding` slot or settings-based Qwen/fake). Fake provider
counts as configured for offline/dev (preserves deterministic smoke).

### `dense_sparse`

1. Always run dense retrieval (unchanged).
2. If sparse **not** configured → fuse dense + BM25 via existing RRF helper
   (extend accumulator to accept BM25 results the same way it accepts
   lexical/sparse). Emit `fallback_reason=sparse_provider_unavailable`.
3. If sparse **configured** → try sparse query embed + sparse retrieval.
   - Success → fuse dense + sparse as today.
   - Any failure → fuse dense + BM25 with a specific `fallback_reason`:
     - `sparse_provider_error` — provider factory or runtime slot failure
     - `sparse_query_embed_failed` — embed call failed
     - `sparse_retrieval_failed` — sparse vector search failed

### `sparse`

1. If sparse not configured → BM25-only results;
   `fallback_reason=sparse_provider_unavailable`, effective strategy `bm25`.
2. If configured and succeeds → sparse-only as today.
3. If configured and fails → BM25-only with `fallback_reason` set to
   `sparse_provider_error`, `sparse_query_embed_failed`, or
   `sparse_retrieval_failed` (same codes as `dense_sparse`).

### Unchanged

- Explicit `strategy=bm25` stays opt-in Okapi path (no dense).
- `hybrid_rrf` stays dense + Postgres lexical FTS (not BM25).
- Hard errors remain for invalid strategy / dense failures / limit validation.

## Observability

- Propagate `fallback_reason` on `RetrievalSearchResult` (already supported).
- Chat audit summary already lifts `fallback_reason` from results; extend tests
  so sparse→BM25 appears there.
- Retrieval metadata should still expose ranks/scores for the legs that ran
  (`bm25_rank` / `sparse_rank` / `dense_rank` as applicable).

## Testing

- Unit/integration: `dense_sparse` without sparse provider → dense+BM25, no
  hard error.
- Provider that raises on `embed_query` → BM25 fallback + reason.
- Happy path with fake/static sparse → still dense+sparse (no spurious
  fallback).
- Explicit `sparse` without provider → BM25, not 500.
- Chat path inherits via `LazyChatRetrievalSearcher` / default strategy
  (smoke or existing chat retrieval tests updated).

## Risks / notes

- Current BM25 scores over **filtered candidate set** (workspace + filters),
  not a global corpus IDF — same as today; document as known limitation.
- RRF fusion currently typed for lexical/sparse; BM25 must plug into the same
  fusion without inventing a third public hybrid name.
- Do not auto-switch chat router route names unless needed; keep public
  strategy name `dense_sparse` as the default request, with fallback inside.

## Open follow-ups (out of this change)

- Optional: promote BM25 into `hybrid_rrf` instead of Postgres lexical (not
  requested).
- Optional: empty sparse hit set (configured but no indexed vectors) → BM25;
  deferred unless we hit it in tests (availability rule is config-only).
