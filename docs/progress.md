# Progreso de Adaptive RAG

## Milestone activo

Pendiente definir M8.

## Ultimo milestone completado

M7 Provider runtime cerrado el 2026-06-19.

## Ultimo slice completado

M7 `m7-quality-gate`: valida tests, lint, types, OpenSpec, smokes fake y
smokes live de Qwen; archiva `m7-provider-runtime-plan` y publica la spec
canonica `openspec/specs/provider-runtime/spec.md`.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run adaptive-rag providers embedding-smoke --text alpha
uv run adaptive-rag providers chat-smoke --message "What supports alpha?"
npx --yes @fission-ai/openspec validate m7-provider-runtime-plan --strict
npx --yes @fission-ai/openspec archive m7-provider-runtime-plan --yes
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Tambien se validaron smokes live de Qwen cargando `.env` local, sin registrar
secretos: embedding smoke con `qwen`/`text-embedding-v4` y chat smoke con
`qwen`/`qwen-plus`, ambos con HTTP 200.

## Change OpenSpec activo

- Ninguno.

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

## Siguiente tarea recomendada

- Abrir un change OpenSpec para M8 antes de implementar mas runtime. La opcion
  recomendada es `m8-live-provider-evals-plan`, porque Qwen ya tiene smokes
  live acotados y la siguiente validacion de riesgo es medir calidad/costo en
  evals hosted antes de streaming, dashboards o persistencia de conversaciones.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
