# Progreso de Adaptive RAG

## Milestone activo

Ninguno. No hay changes OpenSpec activos despues de archivar M24.

## Ultimo milestone completado

M24 Ingestion ops surface cerrado el 2026-06-23.

M24 agrega el camino publico explicito para encolar ingestion de sources,
listar/ver jobs, ejecutar el siguiente job y reintentar jobs blocked/dead_letter
por API, CLI y frontend. Crear sources sigue sin encolar ingestion
automaticamente: el usuario dispara ingestion desde superficies publicas y puede
ver estado/error antes de retry. El change quedo archivado en
`openspec/changes/archive/2026-06-23-m24-ingestion-ops-surface/` y publica la
spec canonica `ingestion-ops-surface`.

El producto v1 terminado mantiene dense retrieval como default, rerank como
opt-in medible y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen
sparse retrieval, Contextual Retrieval generado, auth multi-user, PDF/Office,
voice y MCP server siguen fuera del default salvo nueva evidencia/OpenSpec.
La brecha principal ahora es producto: onboarding local, migraciones/seed/demo
con datos propios y un gate de release real que pruebe el flujo completo sin
fixtures internas como camino principal.

## Ultimo slice completado

M24 `m24-quality-gate`: completa ingestion ops por API/CLI/frontend, valida
backend, frontend y OpenSpec, y archiva `m24-ingestion-ops-surface`.

Comandos validados en el cierre M24:

```text
uv run pytest
uv run ruff check .
uv run mypy src
uv run alembic heads
pnpm --dir frontend test
pnpm --dir frontend run typecheck
pnpm --dir frontend run lint
pnpm --dir frontend run build
npx --yes @fission-ai/openspec validate m24-ingestion-ops-surface --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-23-m24-ingestion-ops-surface/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/product-authoring-surface/spec.md`
- `openspec/specs/ingestion-ops-surface/spec.md`
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

- Abrir `m25-first-run-onboarding`. La opcion recomendada es cerrar primero el
  setup local, migraciones, seed/demo y guia de datos propios, porque M24 ya
  permite operar ingestion desde superficies publicas pero la primera corrida
  todavia depende demasiado de conocimiento interno.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
