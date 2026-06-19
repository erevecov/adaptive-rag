# Progreso de Adaptive RAG

## Milestone activo

M5 Chat/tool calling.

## Ultimo milestone completado

M4 Superficie de retrieval cerrado el 2026-06-19.

## Ultimo slice completado

M5 `m5-chat-service-contract`: implemento `adaptive_rag.chat` con contrato
compartido, runner inyectado, tool de retrieval tipada, payloads reutilizables
y tests deterministas sin red.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m5-chat-tool-calling-plan --strict
openspec list
openspec validate --specs --strict
git diff --check
```

## Change OpenSpec activo

- `m5-chat-tool-calling-plan`

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

## Siguiente tarea recomendada

- `m5-chat-api-endpoint`: agregar `POST /projects/{project_id}/chat` como
  adaptador delgado sobre `ChatService`. Es la opcion recomendada porque el
  contrato compartido ya existe y la API debe validarlo antes de exponer el
  mismo flujo por CLI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
