# Rerank Fail-Open Fallback Design

## Context

Rerank is an optional final retrieval stage, but the current implementation
fails the whole request when its provider is missing, misconfigured, over
budget, unavailable, or returns an invalid result. The baseline retrieval has
already produced isolated, filtered, citation-preserving candidates at that
point. Discarding those candidates makes an optional quality improvement a
hard availability dependency.

The canonical retrieval specification already requires rerank results to
report either successful use or an explained fallback. This change completes
that contract without changing the selected retrieval strategy, ranking
algorithms, provider retry policy, or global rerank defaults.

## Goals

- Return the bounded baseline ranking when rerank cannot run for an operational
  reason.
- Cover missing or incomplete configuration, provider failures, invalid
  provider results, and exhausted provider budget.
- Preserve workspace isolation, metadata filters, citations, strategy scores,
  deterministic ordering, and the requested final result limit.
- Expose stable, secret-safe fallback metadata through API, CLI, chat, and the
  audit trail.
- Continue surfacing unexpected programming errors instead of hiding them.

## Non-goals

- Changing Qwen retry counts, timeout behavior, or HTTP retry eligibility.
- Adding a second rerank model or rerank-provider failover.
- Changing retrieval, rerank, or provider defaults.
- Adding frontend controls or notification UI.
- Making hosted rerank part of offline CI.

## Considered Approaches

### 1. Canonical service policy with thin runtime adapters

`RetrievalService` owns the fail-open policy after baseline candidate
retrieval. API and CLI adapters translate only provider configuration failures
into an absent optional reranker. Runtime factories and hosted eval setup stay
strict when called directly.

This is the selected approach because all product retrieval surfaces share one
ranking and metadata policy while direct runtime validation remains useful for
operators and evals.

### 2. Resilient rerank-provider decorator

A provider wrapper could convert construction and request failures into a
synthetic response. It would add an indirect provider state, make invalid
results harder to distinguish from valid empty responses, and risk weakening
strict runtime validation outside product retrieval.

### 3. Independent fallback in API, CLI, and chat

Each surface could catch rerank errors and repeat the baseline request. This
duplicates behavior, may call retrieval twice, and makes limits, metadata, and
audit semantics prone to drift.

## Architecture

### Runtime resolution

Rerank provider factories keep their current strict contract. The product
retrieval adapters for API and CLI catch `ProviderConfigurationError` only
when a request explicitly enables rerank and pass `reranker=None` to
`RetrievalService`. Dense and sparse provider configuration remains fail-closed
because those providers are required by their selected retrieval strategies.

Hosted eval setup and direct calls to `get_rerank_provider()` continue to
raise configuration errors. This prevents a benchmark from silently measuring
baseline retrieval when it was intended to measure rerank.

### Retrieval flow

1. Validate query, final `limit`, strategy, and rerank candidate limit.
2. Retrieve up to `candidate_limit` baseline candidates using the requested
   strategy.
3. Return normally if rerank was not requested or no candidates exist.
4. If no reranker was resolved, return the first `limit` baseline candidates
   with `rerank_not_configured` metadata.
5. If rerank succeeds and its result is valid, apply the existing reranked
   ordering and metadata.
6. If rerank is blocked by budget, return the first `limit` baseline candidates
   with `rerank_budget_exceeded` metadata.
7. If the provider fails or its result violates the rerank result contract,
   return the first `limit` baseline candidates with `rerank_unavailable`
   metadata.
8. Propagate all other exception types.

The fallback never runs retrieval a second time. The preserved baseline order
is therefore the exact dense, lexical, BM25, sparse, graph, hybrid RRF, or
dense-sparse order already computed for the request.

## Failure Classification

The public fallback reasons are stable operational codes:

- `rerank_not_configured`: no optional reranker could be built because its
  runtime slot, model, credentials, or endpoint configuration was absent or
  incomplete.
- `rerank_budget_exceeded`: the provider budget guard rejected or stopped the
  rerank call.
- `rerank_unavailable`: the provider returned an HTTP, transport, timeout,
  parsing, or rerank-result contract failure.

Raw provider error strings, response bodies, credentials, headers, and request
payloads are not copied into result metadata. Provider usage tracking retains
its existing success/failure records.

`ProviderBudgetExceededError`, `RerankProviderError`, and the known validation
errors produced while applying a `RerankResult` are operational fallback
inputs. Unexpected exceptions such as arbitrary `RuntimeError` continue to
fail the request so application bugs remain visible.

## Result Contract

Each fallback result preserves its original `chunk_id`, distance, score,
citation, embedding metadata, retrieval metadata, strategy, and relative
order. At most the requested final `limit` results are returned.

The result adds stage-specific metadata:

```json
{
  "fallback_reason": "rerank_unavailable",
  "rerank_metadata": {
    "candidate_limit": 10,
    "fallback_reason": "rerank_unavailable",
    "used_rerank": false
  }
}
```

If a result already carries a top-level fallback reason from an earlier stage,
such as graph retrieval, that reason is preserved. The rerank reason remains
available in `rerank_metadata.fallback_reason`, so neither degradation is
lost. Otherwise the rerank reason is also placed in the existing top-level
`fallback_reason` field for current serializers and audit summaries.

Successful rerank metadata remains backward compatible and continues to set
`used_rerank=true` with provider, model, rank, and score details.

## Audit Semantics

The chat audit trail currently treats the presence of `rerank_metadata` as
proof that rerank was used. Fallback metadata makes that inference invalid.
Audit persistence will instead read the explicit `used_rerank` boolean and
will store `false` for degraded results. Rerank score remains null on fallback,
while the retrieval tool result summary records both the existing top-level
`fallback_reason` and a stage-specific `rerank_fallback_reason` read from
rerank metadata. The summary is already schemaless JSON, so this needs no
database migration and preserves both graph and rerank degradation reasons.

## Surface Behavior

- Retrieval API returns HTTP 200 with baseline results and fallback metadata.
- Retrieval CLI exits successfully and emits the same serialized results.
- Chat API and CLI continue the turn with baseline citations instead of
  emitting a retrieval/answer error.
- Hosted eval configuration remains fail-closed before the run starts.
- Requests with rerank disabled do not resolve a rerank provider and retain
  their current payloads without rerank metadata.

## Specification Changes

The canonical `retrieval-quality` OpenSpec will gain scenarios for operational
rerank fallback, bounded baseline results, stable reason codes, preservation of
an earlier fallback reason, and propagation of unexpected errors. Existing
requirements for prefiltered candidates, secret safety, explicit enablement,
and strict provider validation remain unchanged.

## Test Strategy

TDD coverage will prove:

- missing reranker returns bounded baseline results with
  `rerank_not_configured`;
- provider and budget errors return bounded results with their distinct reason;
- invalid, empty, duplicate, and unknown-candidate rerank results degrade with
  `rerank_unavailable`;
- an unexpected exception still propagates;
- baseline order, fields, citations, strategy metadata, and an earlier graph
  fallback reason are preserved;
- successful rerank behavior remains unchanged;
- API and CLI provider-configuration failures return successful fallback
  payloads;
- chat completes and audit persistence records `used_rerank=false` for a
  fallback plus the stage-specific rerank fallback reason;
- rerank-disabled requests do not construct the provider;
- strict runtime-provider and hosted-eval validation still fail when required
  configuration is missing.

Focused unit and integration suites will be followed by formatting, lint,
strict type checking, strict OpenSpec validation, and the full test suite.

## Compatibility and Rollout

The change is additive for successful responses: existing fields keep their
types and successful rerank payloads do not change. Clients that ignore
`fallback_reason` and `rerank_metadata` continue to consume baseline results.
No schema migration, feature flag, new dependency, or deployment configuration
is required.
