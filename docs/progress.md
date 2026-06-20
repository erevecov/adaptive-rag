# Progreso de Adaptive RAG

## Milestone activo

M10 Retrieval eval datasets y decision gates.

## Ultimo milestone completado

M9 Retrieval quality/rerank cerrado el 2026-06-20.

## Ultimo slice completado

M10 `m10-retrieval-dataset-pack`: agrega una suite offline representativa con
casos de exact match, paraphrase, distractors, metadata filters, multi-evidence
y cobertura marcada para escenarios donde rerank deberia ayudar o mantenerse
estable.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m10-retrieval-eval-datasets-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m10-retrieval-eval-datasets-plan/`

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

## Siguiente tarea recomendada

- Implementar `m10-rerank-ab-reporting`. Es la opcion recomendada porque el
  dataset pack ya cubre los riesgos representativos; ahora conviene convertir
  dense vs rerank en un reporte por caso de mejoras, empates y regresiones antes
  de documentar decision gates.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
