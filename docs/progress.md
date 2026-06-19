# Progreso de Adaptive RAG

## Milestone activo

M4 Superficie de retrieval.

## Ultimo milestone completado

M3 Ingestion y retrieval cerrado el 2026-06-19.

## Ultimo slice completado

M4 `m4-retrieval-surface-plan` creado dentro del change activo
`m4-retrieval-surface-plan`.

Comandos validados:

```text
openspec validate m4-retrieval-surface-plan --strict
openspec validate --specs --strict
openspec list
git diff --check
```

## Change OpenSpec activo

- `m4-retrieval-surface-plan`

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

- `m4-retrieval-service-contract`: implementar el servicio compartido que
  convierte query text en query embedding con provider fake/inyectado y llama a
  `DenseRetriever`. Es la opcion recomendada porque API y CLI deben consumir el
  mismo contrato antes de exponer superficies separadas.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
