# Progreso de Adaptive RAG

## Milestone activo

Pendiente de abrir. M14 quedo completo y archivado el 2026-06-21.

## Ultimo milestone completado

M14 Chat history/read surface cerrado el 2026-06-21.

## Ultimo slice completado

M14 `m14-quality-gate`: valida API/CLI de historial de chat, archiva
`m14-chat-history-read-surface` y publica la spec canonica `chat-history`.
M14 queda como superficie read-only para listar sesiones y consultar detalle
auditable sin re-ejecutar chat/retrieval ni mutar el audit trail.

Comandos validados:

```text
uv run pytest tests/integration/cli/test_chat_cli.py -q
uv run pytest tests/integration/api/test_chat.py -q
uv run pytest
uv run ruff check .
uv run mypy src
uv run adaptive-rag chat sessions list --help
uv run adaptive-rag chat sessions show --help
npx --yes @fission-ai/openspec archive m14-chat-history-read-surface --yes
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- Ninguno.

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

- Abrir un change OpenSpec nuevo para la primera UI/frontend de chat e
  historial sobre los contratos existentes (`POST /chat` y `chat-history`).
  La razon es que M14 ya fijo el contrato backend de lectura; el siguiente
  riesgo es disenar una experiencia usable sin mezclar todavia streaming SSE,
  dashboards o replay.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
