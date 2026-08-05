# Handoff — Bloque A+B complete (M40–M50)

**Date:** 2026-08-05  
**Worktree:** `/Users/ereveco/workspace/adaptive-rag/.worktrees/m40-m50-marathon`

## Stack tip (ordered lineage)

`feat/m50-dense-reindex` @ current HEAD — **includes M40→M50** via stacked bases:

M45 → M46 → M47 → M48 → M49 → M50 (not siblings).

| M | Branch | PR |
|---|--------|-----|
| M40–M44 | feat/m44-ci-compose-gate | #181–#185 |
| M45 | feat/m45-pdf-docx-ingestion | #188 |
| M46 | feat/m46-security-pack | #189 |
| M47 | feat/m47-query-routing | #190 |
| M48 | feat/m48-knowledge-lifecycle | #194 |
| M49 | feat/m49-mcp-stdio | #195 |
| M50 | feat/m50-dense-reindex | #196 |

## Explicit non-actions

- **No v1.0 git tag**
- **No GitHub Release**

## Residual (not done)

- Bloque C experimental: graph live evidence / no_go, LLM-as-judge budgeted,
  durable user memory, retrieval playground UI, UI polish PR
- Human merge of stack + re-gate on `main` before any v1.0 tag

## Verify tip

```bash
git checkout feat/m50-dense-reindex && git pull
test -f src/adaptive_rag/cli/dense.py
test -f src/adaptive_rag/knowledge_lifecycle.py
test -d src/adaptive_rag/mcp_server
uv run pytest tests/unit/test_dense_reindex_cli.py tests/unit/test_mcp_tools.py \
  tests/unit/test_knowledge_lifecycle.py tests/unit/routing tests/unit/security -q
uv run adaptive-rag v1 quality-gate
```
