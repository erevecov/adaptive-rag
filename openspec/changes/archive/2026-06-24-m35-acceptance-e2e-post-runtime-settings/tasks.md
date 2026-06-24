# Tasks M35 acceptance e2e post runtime settings

## 1. Contract

- [x] 1.1 Verify post-merge repo state, active OpenSpec and M34 docs.
- [x] 1.2 Add OpenSpec deltas for provider-runtime and v1-product-completion.
- [x] 1.3 Validate M35 OpenSpec strict before implementation.

## 2. Backend/CLI acceptance

- [x] 2.1 Add failing CLI test for `adaptive-rag acceptance runtime-settings-smoke`.
- [x] 2.2 Add acceptance runner that configures fake runtime settings and catalog.
- [x] 2.3 Resolve effective providers from persisted project settings during the
  smoke.
- [x] 2.4 Emit report JSON with criteria, catalog evidence, runtime settings
  evidence and first-run evidence.
- [x] 2.5 Register acceptance CLI group and output file support.

## 3. Docs

- [x] 3.1 Add runbook for the acceptance smoke.
- [x] 3.2 Update README/progress/roadmap with M35 state and next recommendation.

## 4. Validation

- [x] 4.1 Run focused RED/GREEN CLI tests.
- [x] 4.2 Run full backend/frontend/OpenSpec gates.
- [x] 4.3 Archive M35 and create PR.
