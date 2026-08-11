# Proposal: Rerank fail-open fallback

## Why

Rerank is an optional quality stage, but a missing, unavailable, invalid, or
over-budget reranker currently fails the entire retrieval request after the
baseline strategy has already produced valid isolated candidates. This makes
an optional hosted dependency a hard availability requirement for retrieval
API, CLI, and chat.

The canonical retrieval contract already requires successful rerank use or an
explained fallback. The runtime must complete that contract by preserving the
bounded baseline ranking for known operational rerank failures.

## What Changes

- Make `RetrievalService` return the already computed baseline order, bounded
  to the requested final limit, when rerank is not configured, unavailable,
  invalid, or blocked by budget.
- Expose exactly `rerank_not_configured`, `rerank_unavailable`, or
  `rerank_budget_exceeded` in secret-safe result metadata.
- Keep unexpected exceptions fail-closed so programming defects remain visible.
- Adapt API and CLI product retrieval to treat rerank configuration failures as
  optional-provider absence while preserving strict direct runtime and hosted
  eval validation.
- Persist explicit `used_rerank=false` plus `rerank_fallback_reason` in chat
  audit data without a schema migration.

## Non-goals

- Changing retrieval strategies, ranking algorithms, global defaults, retry
  counts, timeout policy, or HTTP retry eligibility.
- Adding a secondary rerank model or provider failover.
- Adding frontend controls or notifications.
- Changing dense or sparse provider failure semantics.
- Making hosted rerank a requirement of offline CI.

## Validation

- TDD unit coverage for missing providers, provider failures, budget failures,
  invalid results, bounded baseline order, prior fallback preservation, and
  unexpected exceptions.
- API, CLI, and chat coverage for successful degradation.
- Durable audit coverage for explicit rerank use and fallback reasons.
- Ruff, strict mypy, focused and full pytest suites, and strict OpenSpec
  validation.
