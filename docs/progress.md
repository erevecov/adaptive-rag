# Progreso de Adaptive RAG

## Milestone activo

Ninguno. M15 Chat frontend inicial quedo cerrado el 2026-06-21.

## Ultimo milestone completado

M15 Chat frontend inicial cerrado el 2026-06-21.

## Ultimo slice completado

M15 `m15-quality-gate`: valida el frontend completo, mantiene el gate Python en
verde, publica la spec canonica `chat-frontend` y archiva
`m15-chat-frontend-plan`.

Comandos validados en este slice:

```text
cd frontend && pnpm test
cd frontend && pnpm run lint
cd frontend && pnpm run typecheck
cd frontend && pnpm run build
uv run pytest
uv run ruff check .
uv run mypy src
pnpm dlx @fission-ai/openspec validate m15-chat-frontend-plan --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m15-chat-frontend-plan/`

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

## Siguiente tarea recomendada

- Abrir un change OpenSpec nuevo para M16 enfocado en streaming de chat por SSE.
  La opcion recomendada es definir primero contrato, persistencia y fallback del
  stream sobre la UI ya operativa, antes de dashboards, replay o auth final.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
