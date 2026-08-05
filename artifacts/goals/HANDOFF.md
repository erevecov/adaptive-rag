# Handoff — pre-v1 marathon (M40–M44 done)

**Date:** 2026-08-05  
**Worktree:** `/Users/ereveco/workspace/adaptive-rag/.worktrees/m40-m50-marathon`  
**Bloque A:** complete (PRs open, stacked on each other).

## PRs (merge base → tip)

| M | Branch | PR |
|---|--------|-----|
| M40 | `feat/m40-indexing-job-publico` | https://github.com/erevecov/adaptive-rag/pull/181 |
| M41 | `feat/m41-job-queue-hardening` | https://github.com/erevecov/adaptive-rag/pull/182 |
| M42 | `feat/m42-chat-multi-turn` | https://github.com/erevecov/adaptive-rag/pull/183 |
| M43 | `feat/m43-authoring-lifecycle-rbac` | https://github.com/erevecov/adaptive-rag/pull/184 |
| M44 | `feat/m44-ci-compose-gate` | https://github.com/erevecov/adaptive-rag/pull/185 |

Stack tip: `feat/m44-ci-compose-gate` (includes M40–M44). Prefer merge stack in order or squash stack tip.

## Not done (Bloque B — post-v1)

- M45 PDF+DOCX
- M46 Security pack
- M47 Query routing
- M48 Knowledge lifecycle
- M49 MCP stdio
- M50 Dense reindex / contextualization LLM opt-in

## Explicit non-actions

- No `v1.0` git tag
- No GitHub Release

## Local re-gate evidence (fake, this worktree)

```bash
uv run alembic upgrade head
uv run adaptive-rag v1 quality-gate --output artifacts/v1-quality-gate.json
# status=succeeded release_decision=ready_for_v1_0
# deferred_defaults without auth_multi_user

uv run adaptive-rag acceptance runtime-settings-smoke
# status=succeeded (saved artifacts/acceptance-runtime-settings-smoke.json)
```

## Next human step

1. Review/merge PR stack M40→M44 (tip `feat/m44-ci-compose-gate` includes all).
2. After merge, re-run quality-gate + acceptance on `main` if desired.
3. Tag v1.0 only after human re-gate.
