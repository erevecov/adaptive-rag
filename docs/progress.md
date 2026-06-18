# Progreso de Adaptive RAG

## Milestone activo

M3 Ingestion y retrieval.

## Ultimo milestone completado

M2 Dominio y persistencia cerrado el 2026-06-18.

## Ultimo slice completado

M2 `m2-quality-gate` completado el 2026-06-18.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate --specs --strict
openspec list
openspec list --specs
uv run adaptive-rag health
uv run adaptive-rag version
```

## Change OpenSpec activo

- `m3-ingestion-retrieval-plan`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/url-fetch-policy/spec.md`

## Siguiente tarea recomendada

- `m3-ingestion-pipeline`: despues de mergear el plan, conectar sources, jobs,
  parsers y `document_versions` sin chunking, embeddings ni retrieval todavia.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
