# Tasks: Rerank fail-open fallback

## 1. Contract

- [x] 1.1 Add retrieval-quality fallback scenarios.
- [x] 1.2 Add durable chat-audit fallback scenarios.
- [x] 1.3 Validate the active OpenSpec change strictly.

## 2. Retrieval service

- [x] 2.1 Add failing tests for missing, unavailable, budget-blocked, and
  invalid rerank providers.
- [x] 2.2 Add failing tests for bounded order, prior fallback preservation, and
  unexpected exception propagation.
- [x] 2.3 Implement the canonical service fallback and stable metadata.
- [x] 2.4 Run the full retrieval unit suite.

## 3. Product adapters

- [x] 3.1 Add failing API and CLI tests for missing rerank configuration.
- [x] 3.2 Convert optional rerank configuration errors to provider absence in
  API and CLI product adapters.
- [x] 3.3 Verify API, CLI, and chat successful rerank regressions.

## 4. Audit

- [x] 4.1 Add failing durable audit tests for fallback metadata.
- [x] 4.2 Persist explicit rerank use and stage-specific fallback reason.
- [x] 4.3 Verify chat completes with baseline citations on rerank failure.

## 5. Validation

- [x] 5.1 Run focused regression suites.
- [x] 5.2 Run Ruff formatting, Ruff lint, strict mypy, and diff checks.
- [ ] 5.3 Validate the active change and canonical specs strictly.
  - Active change passes strict validation. Canonical validation remains blocked
    by pre-existing SHALL/MUST errors in `llm-judge` and
    `retrieval-playground`.
- [x] 5.4 Run the full pytest suite.
  - The complete backend suite passes with Docker/testcontainers enabled.
- [x] 5.5 Review final scope for unrelated changes.
- [x] 5.6 Run the PostgreSQL v1 quality gate and runtime-settings acceptance E2E.
  - Both report `status=succeeded`, cited chat, and all criteria passed.
