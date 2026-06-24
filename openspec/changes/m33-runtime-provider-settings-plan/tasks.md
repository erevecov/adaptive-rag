# Tasks M33 runtime provider settings plan

## 1. Planning and setup

- [x] 1.1 Refresh `origin/main` and create branch
  `codex/m33-runtime-provider-settings-plan`.
- [x] 1.2 Confirm current OpenSpec active changes and canonical provider/
  frontend specs.
- [x] 1.3 Review the current Adaptive RAG provider runtime contract.
- [x] 1.4 Review BeFlow model-settings/chat-pool/encryption patterns as
  non-authoritative reference.

## 2. OpenSpec change

- [x] 2.1 Add proposal, design and task list for global runtime provider
  settings.
- [x] 2.2 Add provider-runtime delta covering global connections, encrypted
  secrets, fixed slots, chat pool and project overrides.
- [x] 2.3 Add chat-frontend delta covering Runtime settings UI and no-secret
  behavior.
- [x] 2.4 Update progress and roadmap docs with M33 status and sequencing.

## 3. Validation

- [x] 3.1 Run `npx --yes @fission-ai/openspec validate m33-runtime-provider-settings-plan --strict`.
- [x] 3.2 Run `npx --yes @fission-ai/openspec validate --specs --strict --no-interactive`.
- [x] 3.3 Run diff hygiene checks.

## 4. Future implementation slices

- [x] 4.1 Implement `m33-provider-connections-secrets`.
- [ ] 4.2 Implement `m33-global-slot-defaults`.
- [ ] 4.3 Implement `m33-project-runtime-overrides`.
- [ ] 4.4 Implement `m33-runtime-resolution-wiring`.
- [ ] 4.5 Implement `m33-runtime-settings-ui`.
- [ ] 4.6 Run `m33-quality-gate` and archive the change when complete.
