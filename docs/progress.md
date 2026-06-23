# Progreso de Adaptive RAG

## Milestone activo

M30 `m30-qwen-sparse-dense-sparse`.

M30 implementa sparse embeddings Qwen/DashScope, backfill explicito y
`strategy=dense_sparse` como estrategia opt-in antes de pulir frontend. El
objetivo es dejar listo el contrato backend de sparse retrieval sin promoverlo
por defecto: `dense` sigue siendo el default y fallback hasta M31.

## Ultimo milestone completado

M29 Lexical retrieval and RRF cerrado el 2026-06-23.

M29 agrega `strategy=lexical` y `strategy=hybrid_rrf` como estrategias opt-in,
preserva citations originales, expone API/CLI/evals y deja scores
lexical/RRF en audit/history. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m29-lexical-retrieval-rrf/` y actualiza
las specs canonicas `chat-audit-trail`, `evals-baseline`,
`retrieval-quality` y `retrieval-surface`.

## Ultimo slice completado

M29 `m29-lexical-retrieval-rrf`: completa lexical retrieval local, fusion
dense+lexical por RRF y superficies opt-in para API/CLI/evals.

Comandos validados al cerrar M29 y abrir M30:

```text
npx --yes @fission-ai/openspec validate m29-lexical-retrieval-rrf --strict
npx --yes @fission-ai/openspec archive m29-lexical-retrieval-rrf --yes
npx --yes @fission-ai/openspec validate m30-qwen-sparse-dense-sparse --strict
npx --yes @fission-ai/openspec list
```

## Change OpenSpec activo

- `openspec/changes/m30-qwen-sparse-dense-sparse/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m29-lexical-retrieval-rrf/`

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

- Completar M30 en un solo PR: sparse provider Qwen/fake, backfill sobre
  `chunk_sparse_embeddings`, `SparseRetriever`, `strategy=dense_sparse`,
  `sparse_score` en audit/history y docs de uso opt-in.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
