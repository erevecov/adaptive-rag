# Progreso de Adaptive RAG

## Milestone activo

M8 Hosted evals.

## Ultimo milestone completado

M7 Provider runtime cerrado el 2026-06-19.

## Ultimo slice completado

M8 `m8-live-retrieval-eval-runner`: agrega el runner hosted de retrieval sobre
las suites M6, reutilizando `RetrievalService` con el provider live inyectado y
adjuntando `provider_usage` al reporte hosted.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run pytest tests/unit/evals tests/integration/cli/test_evals_cli.py -q
uv run pytest tests/unit/evals/test_hosted_retrieval_runner.py -q
npx --yes @fission-ai/openspec validate m8-live-provider-evals-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Este slice usa provider fake con tracker de usage/cost en tests; no ejecuta
llamadas live ni requiere credenciales.

## Change OpenSpec activo

- `openspec/changes/m8-live-provider-evals-plan/`

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

- Implementar `m8-live-chat-eval-runner`. Es el siguiente slice recomendado
  porque retrieval hosted ya produce reportes de calidad/costo; falta sumar
  chat hosted reutilizando `ChatService`, la tool de retrieval y la validacion
  de citations antes de exponer el modo hosted en la CLI.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
