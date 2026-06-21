# Progreso de Adaptive RAG

## Milestone activo

M15 Chat frontend inicial.

## Ultimo milestone completado

M14 Chat history/read surface cerrado el 2026-06-21.

## Ultimo slice completado

M15 `m15-frontend-scaffold`: crea `frontend/` con React/TypeScript/Vite usando
`pnpm`, agrega scripts `dev`, `build`, `lint`, `test`, `typecheck`, lockfile
`pnpm-lock.yaml`, `.env.example` y README local. El scaffold no integra todavia
el backend ni el cliente API.

Comandos validados en este slice:

```text
pnpm create vite frontend --template react-ts
pnpm install
cd frontend && pnpm run lint
cd frontend && pnpm run test
cd frontend && pnpm run build
pnpm dlx @fission-ai/openspec validate m15-chat-frontend-plan --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `m15-chat-frontend-plan`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m14-chat-history-read-surface/`

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

## Siguiente tarea recomendada

- Implementar `m15-chat-api-client`: agregar tipos y cliente `fetch` para
  `POST /chat`, listado de sesiones y detalle read-only. La razon es que el
  scaffold ya fija tooling y lockfile; el siguiente riesgo es alinear el
  contrato TypeScript con los schemas HTTP existentes antes de construir UI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
