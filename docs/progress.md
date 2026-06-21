# Progreso de Adaptive RAG

## Milestone activo

M13 Chat audit trail.

## Ultimo milestone completado

M12 Retrieval evidence expansion cerrado el 2026-06-20.

## Ultimo slice completado

M13 `m13-quality-gate`: valida la implementacion completa de los slices
`3.1`-`3.5` en la branch `codex/m13-chat-audit-trail-impl`. El change OpenSpec
`m13-chat-audit-trail` sigue activo/no archivado hasta que se solicite archive
explicito.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m13-chat-audit-trail --strict
npx --yes @fission-ai/openspec validate --specs --strict
uv run pytest tests/integration/cli/test_chat_cli.py -q
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m13-chat-audit-trail/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-20-m12-retrieval-evidence-expansion/`

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

- Revisar y mergear la branch de implementacion de M13 cuando corresponda,
  manteniendo `m13-chat-audit-trail` activo/no archivado hasta que se solicite
  el archive explicito. La razon es que el gate ya confirma tests, lint, types,
  OpenSpec y smokes CLI, pero el archive no fue solicitado en esta tarea.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
