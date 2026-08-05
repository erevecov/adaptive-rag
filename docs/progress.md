# Progreso de Adaptive RAG

## Milestone activo

Bloque B post-v1 en curso. M45 cerrado. Proximo: M46 Security pack.
Tag v1.0 sigue siendo decision humana (no creado en este trabajo).

## Ultimo milestone completado

M45 PDF + DOCX ingestion (texto embebido) cerrado el 2026-08-05.

Parsers `pdf_embedded` / `docx_text` con registry por content-type y
`source_type`, authoring `pdf`/`docx` via `content_base64`, CLI `--file`,
URL PDF/DOCX post-fetch, frontend file picker, path publico ingest+index+chat.
`pdf_office_ingestion` permanece en quality-gate deferred (sin smoke gate
dedicado). OpenSpec `m45-pdf-docx-ingestion`. **No se creo tag v1.0.**

## Milestone anterior completado

M44 CI + compose all-in-one + gate reconcile cerrado el 2026-08-05.

GitHub Actions CI, compose frontend service, deferred_defaults sin
`auth_multi_user`. **No se creo tag v1.0 ni GitHub Release.**

## Milestone anterior completado

M43 Authoring lifecycle + RBAC closeout cerrado el 2026-08-05.

PATCH/DELETE soft projects/sources (cascade index), DELETE membership,
deactivate user, revoke token, role matrix tests. OpenSpec
`2026-08-05-m43-authoring-lifecycle-rbac`.

## Milestone anterior completado

M42 Chat multi-turn + query condenser cerrado el 2026-08-05.

`session_id` opcional en chat/stream, historial acotado, condensador
deterministico, UI continua sesion seleccionada. OpenSpec archivado
`2026-08-05-m42-chat-multi-turn`.

## Milestone anterior completado

M41 Job queue hardening cerrado el 2026-08-05.

Change archivado en
`openspec/changes/archive/2026-08-05-m41-job-queue-hardening/`.
Worker `run_next` llama `release_expired_leases` y enruta errores inesperados
por `fail()` con backoff/dead-letter. Test kill mid-job (lease vencido)
reencola y re-procesa.

## Milestone anterior completado

M40 Indexing job publico cerrado el 2026-08-05.

Change archivado en
`openspec/changes/archive/2026-08-05-m40-indexing-job-publico/`.
Actualiza specs `ingestion-pipeline`, `ingestion-ops-surface`,
`first-run-onboarding`, `job-queue` y `v1-product-completion`.

Entregado:

- Job publico `index_document_version` (chunk → contextualize → dense/sparse).
- Encadenado tras `ingest_source` exitoso; worker/API `run-next` procesan la
  family de jobs de ingestion/indexing.
- first-run, acceptance y quality-gate drenan el mismo path de jobs (sin
  pipelines de indexing inline privilegiados).
- Tests: source → worker → chunks/embeddings → chat con citations.

## Ultimo slice completado

M40 indexing job publico: path authoring → enqueue → worker → corpus citable.

M39 Chat stepper live events: streaming SSE emite eventos `step`, el snapshot
terminal queda persistido en `ChatHistoryMessage.metadata.steps`, y frontend
renderiza el mismo stepper durante streaming e historial con preferencia
expandido/colapsado en `localStorage`.

Post-M38 Runtime navigation clarity: la navegacion lateral quedo contextual por
area primaria. `Chat` muestra sesiones; `My account` muestra modulos de cuenta
con Appearance y Memory diferido; `Settings` muestra Authoring, Observability y
Runtime con submodulos. Authoring expone Projects, Users, Knowledge y Sources.
Observability expone Summary, Costs, Errors y Latency. Runtime expone
Connections, Model catalog, Global defaults y Project overrides. El generic
`Refresh runtime` fue reemplazado por acciones especificas de cada submodulo.

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
no se creo tag ni GitHub release v1.0. La decision de 2026-08-05 reabre trabajo
pre-v1 (M40–M44) porque el indexing publico y el multi-turn no estan en el
camino de producto UI/API; el tag espera ese cierre.

## Change OpenSpec activo

No active changes found. M45 archivado en
`openspec/changes/archive/2026-08-05-m45-pdf-docx-ingestion/`.
Proximo: OpenSpec `m46-security-pack` (o nombre equivalente).

## Planificacion reciente

2026-08-05 — Plan unificado M40–M50 adoptado:

- Pre-v1 blocker: indexing en job queue (worker hoy solo `document_versions`).
- Pre-v1: job hardening, chat multi-turn + condenser, authoring/RBAC closeout,
  CI + compose all-in-one.
- Post-v1: PDF/DOCX, security pack, query routing, knowledge lifecycle, MCP
  stdio, dense reindex.
- Anti-roadmap: no copiar SaaS/infra de beflow (Supabase, Redis/ARQ, SPLADE,
  voice realtime, sharing publico, etc.).

## Ultimo change archivado

- `openspec/changes/archive/2026-07-06-m39-qwen-runtime-production-defaults/`
- `openspec/changes/archive/2026-07-06-m39-chat-stepper-live-events/`
- `openspec/changes/archive/2026-06-30-runtime-navigation-clarity/`
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
  `origin/main` el release gate final, registrar la evidencia y mantener
  diferida la creacion de tag/GitHub release v1.0 por decision de producto. Si
  se decide una feature adicional antes de release, abrir primero un nuevo
  change OpenSpec desde `origin/main`.

## Reglas de coordinacion

- Usar una branch/worktree por slice de tarea.
- Crear branches desde el `origin/main` actual.
- No correr branches de implementacion paralelas que toquen los mismos archivos.
- Preferir PRs pequenos que se mergeen secuencialmente.
- Usar `docs/progress-log/` solo para blockers, auditorias, handoffs no
  triviales o evidencia que no quede clara en OpenSpec, PR o git.
- Al completar una tarea, recomendar la siguiente y declarar la opcion recomendada con razonamiento.
