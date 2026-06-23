# Progreso de Adaptive RAG

## Milestone activo

M32 Frontend polish esta activo en
`openspec/changes/m32-frontend-polish-plan/`.

El change abre el plan de polish antes de tocar runtime frontend: inventario de
workflows, estados operativos, politica de retrieval default y criterios de QA
visual.

## Ultimo milestone completado

M31 Retrieval strategy gate cerrado el 2026-06-23.

M31 agrega el runner offline `strategy-gate`, JSON estable de decisiones,
soporte de `contextual_summary` en eval fixtures y la CLI
`adaptive-rag evals strategy-gate`. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m31-retrieval-strategy-gate/` y actualiza
las specs canonicas `evals-baseline` y `retrieval-quality`.

## Ultimo slice completado

M31 `m31-retrieval-strategy-gate`: completa el gate comparativo para `dense`,
`contextual_dense`, `lexical`, `hybrid_rrf`, `dense_sparse`, `graph` y
`dense_rerank`. El cierre conserva `dense` como default recomendado; los modos
avanzados no deben entrar al frontend polish por inercia.

Comandos validados al cerrar M31:

```text
npx --yes @fission-ai/openspec validate m31-retrieval-strategy-gate --strict
npx --yes @fission-ai/openspec archive m31-retrieval-strategy-gate --yes
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
npx --yes @fission-ai/openspec list
```

## Change OpenSpec activo

- `openspec/changes/m32-frontend-polish-plan/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m31-retrieval-strategy-gate/`

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

- Completar y mergear `m32-frontend-polish-plan`. La opcion recomendada despues
  del merge es abrir `m32-product-shell-and-authoring`, porque primero conviene
  consolidar shell, project/source authoring e ingestion ops antes de pulir chat
  y observability.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
