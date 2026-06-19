# Progreso de Adaptive RAG

## Milestone activo

Ninguno. Siguiente propuesto: M7 Provider runtime.

## Ultimo milestone completado

M6 Evals cerrado el 2026-06-19.

## Ultimo slice completado

M6 `m6-quality-gate`: valida el milestone completo, archiva
`m6-evals-plan`, publica `openspec/specs/evals-baseline/spec.md` como spec
canonica y deja `openspec list` sin changes activos.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m6-evals-plan --strict
openspec validate --specs --strict
uv run adaptive-rag version
uv run adaptive-rag health
openspec archive m6-evals-plan --yes
openspec list
git diff --check
```

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

## Siguiente tarea recomendada

- Abrir un nuevo change OpenSpec para el siguiente milestone. La opcion
  recomendada es `m7-provider-runtime-plan`, porque M6 dejo evals offline listos
  y la siguiente frontera de riesgo de la v1 es integrar providers live con
  limites de usage/costo antes de agregar evals hosted, dashboards, streaming o
  tuning automatico.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
