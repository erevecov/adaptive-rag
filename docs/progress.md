# Progreso de Adaptive RAG

## Milestone activo

Ninguno. M3 queda cerrado y archivado.

## Ultimo milestone completado

M3 Ingestion y retrieval cerrado el 2026-06-19.

## Ultimo slice completado

M3 `m3-quality-gate` valido el milestone completo y archivo el change
`m3-ingestion-retrieval-plan` como
`openspec/changes/archive/2026-06-19-m3-ingestion-retrieval-plan/`.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate m3-ingestion-retrieval-plan --strict
openspec archive m3-ingestion-retrieval-plan --yes
openspec validate --specs --strict
openspec list
openspec list --specs
uv run adaptive-rag health
uv run adaptive-rag version
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

## Siguiente tarea recomendada

- Crear un nuevo change OpenSpec para M4 antes de implementar chat/tool calling,
  API/CLI de retrieval, evals o providers live. La opcion recomendada es
  planificar primero el siguiente vertical slice sobre el baseline M3 ya
  archivado.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
