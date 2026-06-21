# Progreso de Adaptive RAG

## Milestone activo

M13 Chat audit trail.

## Ultimo milestone completado

M12 Retrieval evidence expansion cerrado el 2026-06-20.

## Ultimo slice completado

M12 `m12-quality-gate`: valida el milestone completo, archiva
`m12-retrieval-evidence-expansion` y publica la spec canonica actualizada de
`retrieval-quality`.

Comandos validados:

```text
uv run pytest
uv run ruff check .
uv run mypy src
npx --yes @fission-ai/openspec validate m12-retrieval-evidence-expansion --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec archive m12-retrieval-evidence-expansion --yes
npx --yes @fission-ai/openspec list
git diff --check
```

Evidencia offline validada:

```text
run_candidate_limit_ab_retrieval_eval_suite sobre `retrieval-dataset-pack`
con embeddings deterministas, `FakeRerankProvider`, SQLite in-memory y
`candidate_limits=(3, 5, 8)`
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

- Completar el PR de planificacion `m13-chat-audit-trail`, validarlo con
  OpenSpec y luego implementar `m13-audit-schema` como primer slice. La razon es
  que schema y relaciones durables deben quedar estables antes de integrar
  repositories, `ChatService`, API/CLI o usage/cost linking.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
