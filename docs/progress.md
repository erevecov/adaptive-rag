# Progreso de Adaptive RAG

## Milestone activo

M32 Frontend polish sigue activo en
`openspec/changes/m32-frontend-polish-plan/`.

El cierre pendiente es `m32-visual-qa-and-docs`: QA responsive y actualizacion
de docs/runbooks sobre la UI de producto ya construida.

## Ultimo milestone completado

M33 Runtime provider settings cerrado el 2026-06-24.

M33 agrega provider connections globales, secrets cifrados, slots fijos,
pool de chat con default unico, overrides por proyecto, resolucion runtime
efectiva para API/CLI y pantalla Runtime settings sin exponer valores secretos.
El change quedo archivado en
`openspec/changes/archive/2026-06-24-m33-runtime-provider-settings-plan/` y
actualiza las specs canonicas `provider-runtime` y `chat-frontend`.

## Ultimo slice completado

M33 `m33-quality-gate`: conecta factories efectivas de chat, dense embedding,
sparse embedding, rerank y contextualization a la configuracion persistida,
agrega UI Runtime settings, valida backend/frontend/OpenSpec y archiva M33.

Comandos validados al cerrar M33:

```text
uv run ruff check .
uv run mypy src
uv run pytest
pnpm test
pnpm lint
pnpm typecheck
pnpm build
npx --yes @fission-ai/openspec validate m33-runtime-provider-settings-plan --strict
npx --yes @fission-ai/openspec archive m33-runtime-provider-settings-plan --yes
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
npx --yes @fission-ai/openspec list
```

## Change OpenSpec activo

- `openspec/changes/m32-frontend-polish-plan/`

## Ultimo change archivado

- `openspec/changes/archive/2026-06-24-m33-runtime-provider-settings-plan/`

## Spec canonica activa

- `openspec/specs/domain-schema/spec.md`
- `openspec/specs/repositories/spec.md`
- `openspec/specs/job-queue/spec.md`
- `openspec/specs/product-authoring-surface/spec.md`
- `openspec/specs/ingestion-ops-surface/spec.md`
- `openspec/specs/first-run-onboarding/spec.md`
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
- `openspec/specs/v1-release-readiness/spec.md`
- `openspec/specs/v1-product-completion/spec.md`

## Siguiente tarea recomendada

- Ejecutar `m32-visual-qa-and-docs` para cerrar QA responsive y docs/runbooks
  de M32. Es la opcion recomendada porque M33 ya esta archivado y no queda otro
  change activo salvo M32.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
