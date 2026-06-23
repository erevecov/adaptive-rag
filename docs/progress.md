# Progreso de Adaptive RAG

## Milestone activo

Ninguno. No hay changes OpenSpec activos despues de M21.

## Ultimo milestone completado

M21 V1 release readiness cerrado el 2026-06-22.

M21 reconcilia el alcance v1.0 contra OpenSpec y el codigo real, agrega el
release package local-first, documenta el demo offline reproducible y archiva
la spec `v1-release-readiness`.

El corte v1.0 mantiene dense retrieval como default, rerank como opt-in medible
y graph/Neo4j como opt-in `hold_default`. Lexical/RRF, Qwen sparse retrieval,
Contextual Retrieval generado, auth multi-user, PDF/Office, voice y MCP server
quedan diferidos post-v1 salvo nueva evidencia/OpenSpec.

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

- Ninguno.

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

- M21 ya esta mergeado en `main`. Siguiente decision recomendada: cortar un
  tag/manual release v1.0 despues de regenerar evidencia fresca con el
  gate/demo offline. Si no se corta release todavia, abrir el primer change
  post-v1 para authoring de projects/sources.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
