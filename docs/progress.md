# Progreso de Adaptive RAG

## Milestone activo

Ninguno. No hay changes OpenSpec activos despues de archivar M23.

## Ultimo milestone completado

M23 Product authoring surface cerrado el 2026-06-23.

M23 agrega la superficie publica minima para crear/listar/ver projects y
sources por API, CLI y frontend. El milestone mantiene ingestion y job state
fuera de authoring: crear sources no encola jobs, no crea documents, no crea
chunks y no llama providers. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m23-product-authoring-surface/` y publica
la spec canonica `product-authoring-surface`.

El producto v1 terminado mantiene dense retrieval como default, rerank como
opt-in medible y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen
sparse retrieval, Contextual Retrieval generado, auth multi-user, PDF/Office,
voice y MCP server siguen fuera del default salvo nueva evidencia/OpenSpec.
La brecha principal ahora es producto: authoring de projects/sources, ingestion
end-to-end desde superficies publicas, job state visible, onboarding local y
demo con datos propios.

## Ultimo slice completado

M23 `m23-quality-gate`: completa authoring por API/CLI/frontend, valida backend,
frontend y OpenSpec, y archiva `m23-product-authoring-surface`.

Comandos validados en el cierre M23:

```text
uv run pytest
uv run ruff check .
uv run mypy src
pnpm --dir frontend test
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
pnpm --dir frontend run build
npx --yes @fission-ai/openspec validate m23-product-authoring-surface --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m23-product-authoring-surface/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/product-authoring-surface/spec.md`
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

- Abrir `m24-ingestion-ops-surface`. La opcion recomendada es definir primero
  el contrato de ejecucion explicita de ingestion y visibilidad de jobs, porque
  M23 ya permite crear projects/sources pero aun no hay camino publico completo
  para procesarlos end-to-end.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
