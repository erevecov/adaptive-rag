# Progreso de Adaptive RAG

## Milestone activo

M8 Hosted evals.

## Ultimo milestone completado

M7 Provider runtime cerrado el 2026-06-19.

## Ultimo slice completado

M8 `m8-evals-cli-hosted-mode`: expone `adaptive-rag evals run --mode hosted`
con `--max-cost-usd`, construye runtime live Qwen opt-in con tracker compartido
para embeddings/chat y serializa reportes hosted con `provider_usage`.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
uv run pytest tests/integration/cli/test_evals_cli.py tests/unit/test_provider_runtime.py tests/unit/evals -q
uv run pytest tests/integration/cli/test_evals_cli.py::test_evals_run_command_hosted_mode_outputs_provider_usage tests/integration/cli/test_evals_cli.py::test_evals_run_command_hosted_mode_requires_budget -q
uv run pytest tests/unit/test_provider_runtime.py::test_live_qwen_runtime_can_share_usage_tracker -q
npx --yes @fission-ai/openspec validate m8-live-provider-evals-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Este slice usa provider y runner fake inyectados con tracker de usage/cost en
tests; no ejecuta llamadas live ni requiere credenciales. La CLI hosted real
sigue siendo opt-in y exige `.env` con Qwen antes de instanciar clientes live.

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

- Ejecutar `m8-quality-gate`. Es el siguiente slice recomendado porque el
  contrato hosted, runners de retrieval/chat y modo CLI ya estan implementados;
  falta validar el milestone completo, decidir si corre smoke hosted opcional
  con `.env` local y archivar el change `m8-live-provider-evals-plan`.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
