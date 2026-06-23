# Proposal M26 v1 product quality gate

## Why

M25 proves that a local user can reach cited chat through public first-run
inputs, but v1 still lacks a single final gate that turns that flow into release
evidence. The release decision needs to be explicit, machine-readable and
documented so v1.0 is not inferred from partial core readiness or hidden
fixtures.

## What Changes

- Add the `m26-v1-product-quality-gate` OpenSpec change.
- Add `adaptive-rag v1 quality-gate`, a public CLI command that runs the
  first-run product flow and emits a release evidence report.
- Add release criteria for product flow, job state, indexing, cited chat,
  opt-in boundaries and follow-up commands.
- Add `docs/v1-quality-gate.md` and refresh README/progress/roadmap so the
  final gate is the documented v1 release decision path.

## Out of Scope

- No automatic git tag, GitHub release or package publish.
- No hosted Qwen, rerank live, Neo4j, auth, PDF/Office, voice or MCP default.
- No new frontend wizard or admin console.
- No change to dense retrieval as the default product path.
