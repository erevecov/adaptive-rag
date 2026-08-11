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

- [ ] 3.1 Add failing API and CLI tests for missing rerank configuration.
- [ ] 3.2 Convert optional rerank configuration errors to provider absence in
  API and CLI product adapters.
- [ ] 3.3 Verify API, CLI, and chat successful rerank regressions.

## 4. Audit

- [ ] 4.1 Add failing durable audit tests for fallback metadata.
- [ ] 4.2 Persist explicit rerank use and stage-specific fallback reason.
- [ ] 4.3 Verify chat completes with baseline citations on rerank failure.

## 5. Validation

- [ ] 5.1 Run focused regression suites.
- [ ] 5.2 Run Ruff formatting, Ruff lint, strict mypy, and diff checks.
- [ ] 5.3 Validate the active change and canonical specs strictly.
- [ ] 5.4 Run the full pytest suite.
- [ ] 5.5 Review final scope for unrelated changes.
