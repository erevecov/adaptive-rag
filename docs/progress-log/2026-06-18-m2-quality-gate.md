# 2026-06-18 M2 quality gate aprobado

## Contexto

M2 Dominio y persistencia quedo integrado en `main` con los slices
`m2-domain-schema`, `m2-repositories`, `m2-job-queue` y
`m2-url-fetch-policy`. El cierre de milestone valida que no queden changes
OpenSpec activos y deja el handoff hacia ingestion/retrieval.

## Evidencia

Quality gate ejecutado desde `codex/m2-quality-gate` sobre `origin/main`:

```text
uv run pytest
uv run ruff check .
uv run mypy src
openspec validate --specs --strict
openspec list
openspec list --specs
uv run adaptive-rag health
uv run adaptive-rag version
uv run python -c "from adaptive_rag.api.app import create_app; app = create_app(); print(app.title)"
```

Outputs observados:

```text
110 passed
All checks passed!
Success: no issues found in 31 source files
4 passed, 0 failed
No active changes found.
domain-schema requirements 5
repositories requirements 4
job-queue requirements 4
url-fetch-policy requirements 3
ok
adaptive-rag 0.1.0
Adaptive RAG
```

## Decision

M2 queda cerrado. Los contratos canonicos vigentes son:

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/url-fetch-policy/spec.md`

## Siguiente paso recomendado

Crear `m3-ingestion-retrieval-plan` como primer change OpenSpec de M3 antes de
implementar codigo nuevo, para separar ingestion, chunking, embeddings y
retrieval en slices revisables.
