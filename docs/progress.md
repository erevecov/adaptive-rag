# Progreso de Adaptive RAG

## Milestone activo

M29 `m29-lexical-retrieval-rrf`.

M29 implementa lexical retrieval local y `hybrid_rrf` como estrategias opt-in
antes de pulir frontend. El objetivo es cubrir terminos exactos, codigos e
identificadores sin promover nada por defecto: `dense` sigue siendo el default y
fallback hasta M31.

## Ultimo milestone completado

M28 Contextual Retrieval generated summaries cerrado el 2026-06-23.

M28 genera y persiste `contextual_summary` durante indexing local, wirea
first-run/v1 gate para reportar contextualized counts y mantiene citations
ancladas al texto original. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m28-contextual-retrieval-generated-summaries/`
y actualiza las specs canonicas `embedding-baseline` y `first-run-onboarding`.

## Ultimo slice completado

M28 `m28-contextual-retrieval-generated-summaries`: completa generacion local de
contexto por chunk, valida first-run/gate y archiva
`m28-contextual-retrieval-generated-summaries`.

Comandos validados al cerrar M28 y abrir M29:

```text
npx --yes @fission-ai/openspec validate m28-contextual-retrieval-generated-summaries --strict
npx --yes @fission-ai/openspec validate m29-lexical-retrieval-rrf --strict
npx --yes @fission-ai/openspec list
```

## Change OpenSpec activo

- `openspec/changes/m29-lexical-retrieval-rrf/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m28-contextual-retrieval-generated-summaries/`

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

- Completar y mergear M29 como PR de backend contract. Despues abrir M30 para
  Qwen sparse / `dense_sparse`, verificando documentacion provider actual antes
  de codificar payloads, storage o costos.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
