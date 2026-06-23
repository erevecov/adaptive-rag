# Progreso de Adaptive RAG

## Milestone activo

M28 `m28-contextual-retrieval-generated-summaries`.

M28 implementa el primer slice del nuevo alcance post-v1: generar
`contextual_summary` durante indexing local, antes de embeddings, para activar
Contextual Retrieval sin cambiar el default `dense` ni agregar una nueva rama de
ranking. La evidencia publica sale por `adaptive-rag first-run smoke` y el gate
v1 reutiliza ese reporte.

## Ultimo milestone completado

M27 Post-v1 retrieval expansion cerrado el 2026-06-23.

M27 abre el nuevo alcance post-v1 para dejar listas capacidades avanzadas de
retrieval antes de pulir frontend. El objetivo aprobado es opt-in y medible:
Contextual Retrieval generado, lexical/RRF, Qwen sparse / `dense_sparse` y un
gate comparativo posterior. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m27-retrieval-expansion-plan/` y actualiza
la spec canonica `retrieval-quality`.

## Ultimo slice completado

M27 `m27-retrieval-expansion-plan`: completa el plan post-v1 para retrieval
avanzado, valida OpenSpec/docs y archiva `m27-retrieval-expansion-plan`.

Comandos validados al cerrar M27 y abrir M28:

```text
npx --yes @fission-ai/openspec validate m27-retrieval-expansion-plan --strict
npx --yes @fission-ai/openspec validate m28-contextual-retrieval-generated-summaries --strict
npx --yes @fission-ai/openspec list
```

## Change OpenSpec activo

- `openspec/changes/m28-contextual-retrieval-generated-summaries/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m27-retrieval-expansion-plan/`

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

- Completar y mergear M27 como PR de planificacion. Despues abrir
  `m28-contextual-retrieval-generated-summaries`, porque reutiliza campos e
  input builders existentes y estabiliza la rama dense contextual antes de
  agregar lexical/RRF o sparse.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
