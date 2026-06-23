# Progreso de Adaptive RAG

## Milestone activo

M22 V1 product scope reset.

M22 redefine v1 como producto local-first single-user terminado. M21 queda como
evidencia de core/pre-v1 y no como autorizacion para cortar tag o release
v1.0.

## Ultimo milestone completado

M21 V1 core/readiness cerrado el 2026-06-22.

M21 reconcilia el alcance v1.0 contra OpenSpec y el codigo real, agrega el
release package local-first, documenta el demo offline reproducible y archiva
la spec `v1-release-readiness`. Despues del reset M22, esa evidencia se trata
como readiness del core, no como producto v1 terminado.

El producto v1 terminado mantiene dense retrieval como default, rerank como
opt-in medible y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen
sparse retrieval, Contextual Retrieval generado, auth multi-user, PDF/Office,
voice y MCP server siguen fuera del default salvo nueva evidencia/OpenSpec.
La brecha principal ahora es producto: authoring de projects/sources, ingestion
end-to-end desde superficies publicas, job state visible, onboarding local y
demo con datos propios.

## Ultimo slice completado

M21 `m21-release-quality-gate`: valida frontend, Python, OpenSpec, compose
config y smokes CLI; archiva el change M21 y publica la spec canonica
`v1-release-readiness`.

Comandos validados en el gate M21:

```text
pnpm --dir frontend test
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
uv run pytest
pnpm --dir frontend run build
uv run ruff check .
uv run mypy src
uv run adaptive-rag version
uv run adaptive-rag health
docker compose config
npx --yes @fission-ai/openspec validate m21-v1-release-readiness-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m22-v1-product-scope-reset/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-22-m21-v1-release-readiness-plan/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
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

## Siguiente tarea recomendada

- Completar M22 y abrir el primer slice de producto terminado:
  `m23-product-authoring-surface`. La opcion recomendada es empezar por
  authoring de projects/sources porque desbloquea ingestion con datos propios,
  onboarding real y demo final sin fixtures internas.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
