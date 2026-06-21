# Progreso de Adaptive RAG

## Milestone activo

Ninguno. M17 quedo cerrado y archivado.

## Ultimo milestone completado

M17 Chat observability y costo-latencia cerrado el 2026-06-21.

## Ultimo slice completado

M17 `m17-quality-gate`: valida Python/OpenSpec/docs, archiva
`m17-chat-observability` y publica la spec canonica `chat-observability`.

Comandos validados en este slice:

```text
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
pnpm dlx @fission-ai/openspec validate m17-chat-observability --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec archive m17-chat-observability --yes
pnpm dlx @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-21-m17-chat-observability/`

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

## Siguiente tarea recomendada

- Definir el siguiente milestone o abrir un nuevo change OpenSpec desde el
  backlog futuro. El candidato documentado es evaluar Neo4j como graph DB
  routeable, pero conviene confirmarlo antes de iniciar implementacion.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
