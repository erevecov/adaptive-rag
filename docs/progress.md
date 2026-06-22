# Progreso de Adaptive RAG

## Milestone activo

M19 Graph live ops evidence.

Objetivo: medir y operar Neo4j live como indice derivado opt-in antes de
considerar cualquier promocion de graph retrieval. `dense` sigue como default y
`graph` sigue limitado a experimentos controlados.

## Ultimo milestone completado

M18 Neo4j graph DB decision cerrado el 2026-06-22.

## Ultimo slice completado

M19 `m19-graph-live-evidence-report`: agrega
`adaptive-rag evals graph-live-evidence` para consolidar el quality gate
dense-vs-graph con reportes live de backfill/reindex, retrieval smoke, error
codes, latencia/fallback y costo operacional graph declarado. El comando no
ejecuta operaciones live por si mismo; consume artefactos JSON previos y sale
con codigo no cero si calidad u operaciones live fallan.

Comandos validados en este slice:

```text
uv run pytest tests/unit/evals/test_graph_live_evidence_report.py tests/integration/cli/test_evals_cli.py -q
uv run ruff check src tests
uv run mypy src/adaptive_rag
pnpm dlx @fission-ai/openspec validate m19-graph-live-ops-plan --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
uv run pytest
git diff --check
```

## Change OpenSpec activo

- `openspec/changes/m19-graph-live-ops-plan/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-22-m18-neo4j-graph-db-decision/`

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
- `openspec/specs/chat-audit-trail/spec.md`
- `openspec/specs/chat-history/spec.md`
- `openspec/specs/chat-frontend/spec.md`
- `openspec/specs/chat-streaming/spec.md`
- `openspec/specs/chat-observability/spec.md`
- `openspec/specs/graph-store/spec.md`

## Siguiente tarea recomendada

- Ejecutar `m19-quality-gate`: correr el set completo de validaciones,
  reconciliar la decision `hold_default`, `limited_experiment` o
  `no_go_promotion`, archivar el change OpenSpec y publicar la spec canonica.
  Es la opcion recomendada porque ya existen los artefactos de setup,
  backfill/reindex, retrieval smoke y evidencia consolidada.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
