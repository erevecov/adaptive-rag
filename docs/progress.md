# Progreso de Adaptive RAG

## Milestone activo

M7 Provider runtime.

## Ultimo milestone completado

M6 Evals cerrado el 2026-06-19.

## Ultimo slice completado

M7 `m7-provider-runtime-plan`: crea el change OpenSpec para integrar providers
live de forma opt-in, manteniendo fake providers/runners como default,
definiendo limites de usage/costo y separando smokes live de tests/evals offline.

Comandos validados:

```text
uv sync --extra dev
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m7-provider-runtime-plan --strict
openspec validate --specs --strict
openspec list
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m7-provider-runtime-plan/`

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

- Implementar `m7-provider-settings-contract`. Es el primer slice recomendado
  porque las factories y settings de runtime deben quedar estables antes de
  agregar adapters live de embeddings/chat o limites de costo.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
