# Progreso de Adaptive RAG

## Milestone activo

M31 `m31-retrieval-strategy-gate`.

M31 compara `dense`, `contextual_dense`, `lexical`, `hybrid_rrf`,
`dense_sparse`, `graph` y `dense_rerank` antes de pulir frontend. El objetivo
es emitir evidencia y decision por estrategia sin cambiar el default por
inercia: `dense` sigue siendo default salvo que el gate recomiende promocion.

## Ultimo milestone completado

M30 Qwen sparse dense_sparse cerrado el 2026-06-23.

M30 agrega sparse embeddings Qwen/DashScope, backfill explicito,
`SparseRetriever`, `strategy=dense_sparse` opt-in y `sparse_score` en
audit/history. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m30-qwen-sparse-dense-sparse/` y actualiza
las specs canonicas `chat-audit-trail`, `evals-baseline`, `provider-runtime`,
`retrieval-quality` y `retrieval-surface`.

## Ultimo slice completado

M30 `m30-qwen-sparse-dense-sparse`: completa sparse provider Qwen/fake,
backfill sobre `chunk_sparse_embeddings`, `SparseRetriever`, fusion
dense+sparse por RRF y superficies opt-in para API/CLI/evals.

Comandos validados al cerrar M30 y abrir M31:

```text
npx --yes @fission-ai/openspec validate m30-qwen-sparse-dense-sparse --strict
npx --yes @fission-ai/openspec archive m30-qwen-sparse-dense-sparse --yes
npx --yes @fission-ai/openspec validate m31-retrieval-strategy-gate --strict
npx --yes @fission-ai/openspec list
```

## Change OpenSpec activo

- `openspec/changes/m31-retrieval-strategy-gate/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m30-qwen-sparse-dense-sparse/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/product-authoring-surface/spec.md`
- `openspec/specs/ingestion-ops-surface/spec.md`
- `openspec/specs/first-run-onboarding/spec.md`
- `openspec/specs/url-fetch-policy/spec.md`
- `openspec/specs/ingestion-retrieval-plan/spec.md`
- `openspec/specs/ingestion-pipeline/spec.md`
- `openspec/specs/chunking-baseline/spec.md`
- `openspec/specs/embedding-baseline/spec.md`
- `openspec/specs/retrieval-baseline/spec.md`
- `openspec/specs/retrieval-surface/spec.md`
- `openspec/specs/chat-tool-calling/spec.md`
- `openspec/specs/evals-baseline/spec.md`
- `openspec/specs/provider-runtime/spec.md`
- `openspec/specs/hosted-evals/spec.md`
- `openspec/specs/retrieval-quality/spec.md`
- `openspec/specs/chat-audit-trail/spec.md`
- `openspec/specs/chat-history/spec.md`
- `openspec/specs/chat-frontend/spec.md`
- `openspec/specs/chat-streaming/spec.md`
- `openspec/specs/chat-observability/spec.md`
- `openspec/specs/graph-store/spec.md`
- `openspec/specs/v1-release-readiness/spec.md`
- `openspec/specs/v1-product-completion/spec.md`

## Siguiente tarea recomendada

- Completar M31 en un solo PR: runner `strategy-gate`, JSON estable de
  decisiones, soporte de `contextual_summary` en eval fixtures, CLI
  `adaptive-rag evals strategy-gate` y docs de decision antes de frontend
  polish.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
