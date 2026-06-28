# Progreso de Adaptive RAG

## Milestone activo

No hay milestone activo ni changes OpenSpec pendientes de archivar.

Estado post-M38: M36 Functional chat workspace, M37 Project RBAC/chat
knowledge y M38 Chat retrieval/rerank settings quedaron implementados,
validados y archivados. La rama `main` ya contiene el merge funcional de M38 y
este cierre archiva el change en
`openspec/changes/archive/2026-06-28-m38-chat-retrieval-settings/`.

## Ultimo milestone completado

M38 Chat retrieval/rerank settings cerrado el 2026-06-28.

El change quedo archivado en
`openspec/changes/archive/2026-06-28-m38-chat-retrieval-settings/`
y actualiza las specs canonicas `chat-tool-calling` y `provider-runtime`.

## Ultimo slice completado

M38 Chat retrieval/rerank settings: settings efectivos globales y por proyecto
para `retrieval_limit`, `rerank_enabled` y `rerank_candidate_limit` quedaron
persistidos, expuestos por API/frontend y conectados al flujo de chat API/CLI.
Los defaults iniciales son `retrieval_limit=5`, `rerank_enabled=true` y
`rerank_candidate_limit=10`; ambos limites aceptan maximo `50` y el candidate
limit no puede ser menor que el retrieval limit cuando rerank esta activo. El
chat audita la configuracion efectiva sin secretos y construye reranker lazy
solo cuando corresponde. En frontend, Runtime settings maneja defaults globales
y overrides por proyecto; Appearance se movio a `My account` como preferencia
de usuario y ya no vive en settings globales/proyecto. El gate valido backend,
frontend, lint/typecheck, OpenSpec strict, `git diff --check` y QA browser.

M36 Functional chat workspace fue archivado como housekeeping el 2026-06-28.
El archive movio el change a
`openspec/changes/archive/2026-06-28-m36-chat-functional-workspace/` y aplico
sus deltas finales a `openspec/specs/chat-frontend/spec.md`.

M37 Project RBAC/chat knowledge: proyectos compartidos con usuarios,
membresias por proyecto, sesiones privadas por usuario, propuestas de
conocimiento desde chat y revision contributor+ quedaron implementados en
backend/frontend. El gate de cierre valido `uv run pytest -q`, `uv run ruff
check src tests`, `uv run mypy src\adaptive_rag`, tests/lint/typecheck/build de
frontend, OpenSpec strict, Alembic heads y `git diff --check`.

M36 Functional chat workspace: el chat quedo reorganizado como workspace
funcional de tres zonas: rail de sesiones, chat central e inspector derecho con
tabs Context/Minimap. La paleta ya no esta acoplada a Chat: Settings incluye
Appearance con temas globales Light, Dark y Purple, aplicados via `data-theme`,
`.dark` y `localStorage`. Session navigation, context/usage, minimap, action
stepper, source viewer desde citas actuales y chunks historicos, y STT browser
fallback quedaron implementados con tests. M38 movio Appearance a `My account`
como configuracion de usuario. Qwen STT queda deferred porque la
documentacion actual de DashScope requiere ASR con `file_urls`/polling y no
existe contrato backend local de audio. Memory queda deferred tras verificar
que no hay tabla, repositorio ni ruta API durable.

Post-M35 final release gate/audit closeout (PR #142): re-ejecuto desde
`origin/main` el gate final local, confirmo `release_decision=ready_for_v1_0`,
valido el acceptance smoke post-runtime-settings y corrigio la exposicion de
secrets en `repr`.

Comandos validados al cerrar el gate/audit:

```text
uv run adaptive-rag v1 quality-gate --output artifacts\v1-quality-gate.json
uv run adaptive-rag acceptance runtime-settings-smoke --output artifacts\runtime-acceptance.json
uv run pytest
uv run ruff check .
uv run mypy src\adaptive_rag
pnpm --dir frontend test
pnpm --dir frontend typecheck
pnpm --dir frontend lint
pnpm --dir frontend build
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
uv tool run pip-audit --strict
pnpm --dir frontend audit --prod
uv tool run bandit -r src -q
git diff --check
```

Resultado: el producto queda listo segun el gate local (`ready_for_v1_0`), pero
no se creo tag ni GitHub release v1.0. La decision queda diferida
intencionalmente para permitir una feature pre-v1 adicional.

## Change OpenSpec activo

No active changes found.

## Ultimo change archivado

- `openspec/changes/archive/2026-06-28-m38-chat-retrieval-settings/`

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
- `openspec/specs/project-rbac/spec.md`
- `openspec/specs/v1-release-readiness/spec.md`
- `openspec/specs/v1-product-completion/spec.md`

## Siguiente tarea recomendada

- No quedan changes por archivar. La opcion recomendada es re-ejecutar desde
  `origin/main` el release gate final y decidir si crear tag/GitHub release
  v1.0. Si se decide una feature adicional antes de release, abrir primero un
  nuevo change OpenSpec desde `origin/main`.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
