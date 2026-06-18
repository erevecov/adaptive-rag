# Progreso de Adaptive RAG

## Milestone activo

M2 Dominio y persistencia.

## Ultimo milestone completado

M1 Foundation cerrado el 2026-06-17.

## Ultimo slice completado

M2 `m2-job-queue` implementado y archivado el 2026-06-18.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate --specs --strict
```

## Change OpenSpec activo

- Ninguno.

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`

## Siguiente tarea recomendada

- `m2-url-fetch-policy`: implementar proteccion contra SSRF, DNS rebinding,
  redirects inseguros, content type no permitido y tamano maximo de respuesta.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
