# Design: Rerank fail-open fallback

## Decision

`RetrievalService` owns the canonical rerank fail-open policy. Product-facing
API and CLI adapters convert only `ProviderConfigurationError` from optional
rerank construction into `reranker=None`; direct runtime resolution and hosted
eval setup remain strict.

The detailed approved design is recorded in
`docs/superpowers/specs/2026-08-11-rerank-fail-open-fallback-design.md`.

## Data flow

1. Validate query, strategy, final limit, and rerank candidate limit.
2. Compute up to the candidate limit using the requested baseline strategy.
3. Skip provider resolution and metadata when rerank is disabled.
4. Return bounded baseline results with `rerank_not_configured` when the
   optional provider cannot be built.
5. Apply successful rerank results without changing the existing payload.
6. Return bounded baseline results with `rerank_budget_exceeded` for budget
   admission failures.
7. Return bounded baseline results with `rerank_unavailable` for provider or
   rerank-result contract failures.
8. Propagate all other exception types.

Fallback does not repeat retrieval. Each returned item preserves its original
chunk, citation, scores, strategy metadata, order, and any earlier top-level
fallback reason. Rerank fallback remains available in
`rerank_metadata.fallback_reason`; when no prior reason exists, the same value
also populates the existing top-level `fallback_reason`.

## Audit

Audit reads the explicit `rerank_metadata.used_rerank` boolean instead of
inferring use from metadata presence. The schemaless tool result summary stores
`rerank_fallback_reason` independently from an earlier top-level fallback.
Fallback results have no rerank score.

## Safety

Public metadata contains stable codes only. Raw provider errors, response
bodies, headers, credentials, and request payloads are excluded. Known rerank
configuration, budget, provider, parsing, and result-contract errors fail open;
unexpected application errors fail closed.
