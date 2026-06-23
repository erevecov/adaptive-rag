# Roadmap de Adaptive RAG

## Estado actual

- M1 Foundation: completo.
- M2 Dominio y persistencia: completo.
- M3 Ingestion y retrieval: completo.
- M4 Superficie de retrieval: completo.
- M5 Chat/tool calling: completo.
- M6 Evals: completo.
- M7 Provider runtime: completo.
- M8 Hosted evals: completo.
- M9 Retrieval quality/rerank: completo.
- M10 Retrieval eval datasets y decision gates: completo.
- M11 Retrieval strategy decision: completo.
- M12 Retrieval evidence expansion: completo.
- M13 Chat audit trail: completo.
- M14 Chat history/read surface: completo.
- M15 Chat frontend inicial: completo.
- M16 Chat streaming SSE: completo.
- M17 Chat observability y costo-latencia: completo.
- M18 Neo4j graph DB decision: completo.
- M19 Graph live ops evidence: completo.
- M20 Chat observability dashboard: completo.
- M21 V1 core/readiness: completo.
- M22 V1 product scope reset: completo.
- M23 Product authoring surface: completo.
- M24 Ingestion ops surface: completo.
- M25 First-run onboarding: completo.
- M26 V1 product quality gate: completo.
- M27 Post-v1 retrieval expansion: activo.

## M1 Foundation

Estado: completo.

Entregado:

- Scaffold del paquete Python.
- Settings y logging.
- Base SQLAlchemy, helpers de sesion DB y foundation de Alembic.
- App factory de FastAPI y `/health`.
- Shell CLI de Typer con `version` y `health`.
- Quality gate final aprobado el 2026-06-17.

## M2 Dominio y persistencia

Estado: completo.

Secuencia recomendada:

1. `m2-domain-schema`: completo. Modelos SQLAlchemy y migracion Alembic para schema de proyectos, documentos y chunks.
2. `m2-repositories`: completo. Capa de repositories con aislamiento por proyecto y filtros de metadata.
3. `m2-job-queue`: completo. Jobs, job events, retries, estados blocked/dead-letter y leasing de workers.
4. `m2-url-fetch-policy`: completo. Proteccion contra SSRF, DNS rebinding, redirects, content type y tamano de respuesta.
5. `m2-quality-gate`: completo. Validacion del milestone, reconciliacion de docs y handoff hacia M3.

## M3 Ingestion y retrieval

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-19-m3-ingestion-retrieval-plan/`

Secuencia entregada:

1. `m3-ingestion-retrieval-plan`: completo. Creo y archivo el change OpenSpec que delimito los slices de ingestion/retrieval sobre los contratos cerrados de M2.
2. `m3-ingestion-pipeline`: completo en branch de implementacion. Conecta sources, documents, document versions, jobs y `URLFetchPolicy` en un flujo de ingestion verificable con fakes, sin chunking ni embeddings.
3. `m3-chunking-baseline`: completo en branch de implementacion. Implementa chunking semantico inicial con offsets reproducibles para citations.
4. `m3-embedding-baseline`: completo en branch de implementacion. Construye inputs de embedding/contexto y persiste embeddings densos usando provider fakes antes de Qwen live.
5. `m3-retrieval-baseline`: completo en branch de implementacion. Implementa retrieval dense exacto con filtros antes de ranking y citations ancladas a texto normalizado.
6. `m3-quality-gate`: completo. Valida tests, lint, types, specs, CLI smoke y archiva M3.

Continuacion: M4 quedo completado sobre el baseline M3 archivado. La siguiente
decision debe abrir un change OpenSpec nuevo para M5 antes de implementar
chat/tool calling, evals o providers live.

## M4 Superficie de retrieval

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-19-m4-retrieval-surface-plan/`

Secuencia entregada:

1. `m4-retrieval-surface-plan`: completo en branch de planificacion. Crea el
   change OpenSpec que delimita API/CLI de retrieval sobre `DenseRetriever`.
2. `m4-retrieval-service-contract`: completo en branch de implementacion.
   Implementa un servicio compartido que recibe query text, genera query
   embedding con provider inyectado/fake, valida filtros y llama a
   `DenseRetriever`.
3. `m4-retrieval-api-endpoint`: completo en branch de implementacion. Agrega
   `POST /projects/{project_id}/retrieval/search` con request/response JSON,
   metadata filters, dependency overrides en tests y payloads reutilizables por
   la CLI.
4. `m4-retrieval-cli-command`: completo en branch de implementacion. Agrega
   `adaptive-rag retrieval search` usando el mismo servicio, filtros y payloads
   serializables que la API.
5. `m4-quality-gate`: completo. Valida tests, lint, types y specs; archiva el
   change M4 y publica `openspec/specs/retrieval-surface/spec.md`.

Siguiente tarea recomendada: abrir un nuevo change OpenSpec para M5 chat/tool
calling sobre la superficie estable de M4. La opcion recomendada es definir
primero el contrato conversacional y su reutilizacion del servicio compartido,
antes de agregar comportamiento agentico o providers live.

## M5 Chat/tool calling

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-19-m5-chat-tool-calling-plan/`

Spec canonica:

- `openspec/specs/chat-tool-calling/spec.md`

Secuencia entregada:

1. `m5-chat-tool-calling-plan`: completo en branch de planificacion. Crea el
   change OpenSpec que delimita chat/tool calling sobre `RetrievalService`.
2. `m5-chat-service-contract`: completo. Implementa `adaptive_rag.chat` con
   servicio compartido, runner/modelo inyectado, tool de retrieval tipada,
   payloads reutilizables y fakes deterministas.
3. `m5-chat-api-endpoint`: completo. Agrega `POST /projects/{project_id}/chat`
   como adaptador delgado sobre el servicio conversacional, con schemas HTTP,
   dependency overrides y tests deterministas.
4. `m5-chat-cli-command`: completo. Agrega `adaptive-rag chat ask` como
   adaptador delgado sobre el servicio conversacional, reutilizando
   `RetrievalService`, payloads compartidos y filtros CLI.
5. `m5-quality-gate`: completo. Valida tests, lint, types, smokes CLI,
   OpenSpec, archiva el change M5 y publica la spec canonica de
   chat/tool calling.

Continuacion: M5 quedo completado sobre la superficie estable de retrieval de
M4. La siguiente decision debe abrir un change OpenSpec nuevo para M6 antes de
agregar streaming, persistencia de conversaciones o providers live obligatorios.

## M6 Evals

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-19-m6-evals-plan/`: define evaluaciones
  offline de retrieval/chat sobre las superficies estables de M4/M5, con
  datasets versionados, runners deterministas, metricas objetivas, reportes
  JSON y CLI no interactiva.

Spec canonica:

- `openspec/specs/evals-baseline/spec.md`

Secuencia entregada:

1. `m6-evals-plan`: completo en branch de planificacion. Crea el change
   OpenSpec que delimita evals offline antes de providers live, streaming o
   persistencia de conversaciones.
2. `m6-evals-fixtures-contract`: completo. Crea el paquete
   `adaptive_rag.evals` inicial, modelos de casos/resultados y loader de
   fixtures versionados con validacion estricta.
3. `m6-retrieval-eval-runner`: completo. Ejecuta casos de retrieval contra
   `RetrievalService` con provider fake y metricas top-k/expected chunk.
4. `m6-chat-eval-runner`: completo. Ejecuta casos de chat contra
   `ChatService` con runner fake/determinista, retrieval fixture-backed,
   coverage de citations y checks de tool calls esperadas.
5. `m6-evals-cli-reporting`: completo. Agrega `adaptive-rag evals run` con
   salida JSON por stdout o `--output`, thresholds y exit code estable para CI.
6. `m6-quality-gate`: completo. Valida tests, lint, types, CLI smokes
   basicos, OpenSpec, archiva el change M6 y publica la spec canonica de
   evals.

Continuacion: M6 quedo completado sobre retrieval/chat estables y evals offline.
La siguiente decision fue `m7-provider-runtime-plan`, para integrar providers
live con limites de usage/costo y fakes/contract tests antes de depender de red
o credenciales.

## M7 Provider runtime

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-19-m7-provider-runtime-plan/`: define el
  runtime opt-in para providers live de embeddings y chat, con fake default,
  settings/factories configurables, limites de usage/costo, metadata
  estructurada y smokes live separados de tests/evals offline.

Spec canonica:

- `openspec/specs/provider-runtime/spec.md`

Secuencia entregada:

1. `m7-provider-runtime-plan`: completo en branch de planificacion. Crea el
   change OpenSpec que delimita providers live antes de streaming, dashboards,
   hosted evals o tuning automatico.
2. `m7-provider-settings-contract`: completo. Define settings, factories
   API/CLI, fake default y errores estables de configuracion antes de tocar
   SDKs live; modela Qwen como provider live opt-in con
   `ADAPTIVE_RAG_QWEN_API_KEY` y `ADAPTIVE_RAG_QWEN_BASE_URL`.
3. `m7-live-embedding-provider`: agrega el adapter live de embeddings bajo
   `DenseEmbeddingProvider`, manteniendo dimension 1024, tests sin red y smoke
   live opt-in. Completo: agrega `QwenDenseEmbeddingProvider`, cliente HTTP para
   endpoints OpenAI-style o DashScope TextEmbedding, y comando
   `adaptive-rag providers embedding-smoke`.
4. `m7-live-chat-runner`: agrega el runner live de chat/tool calling bajo
   `ChatRunner`, reutilizando la tool de retrieval y la validacion de citations.
   Completo: agrega `QwenChatRunner`, cliente HTTP OpenAI-compatible, factory
   live para `chat_provider=qwen` y smoke CLI
   `adaptive-rag providers chat-smoke`.
5. `m7-usage-cost-limits`: agrega metadata de usage/cost, budget guard,
   timeouts/retries acotados y logging estructurado sin secretos. Completo:
   agrega records estructurados, tracker in-memory, price catalog configurable,
   budget guard y manejo estable de errores de presupuesto en smokes CLI.
6. `m7-quality-gate`: valida el milestone completo, archiva el change M7 y
   publica la spec canonica `provider-runtime`.

Continuacion: M7 cerro la frontera operativa minima de providers live. La
siguiente decision fue `m8-live-provider-evals-plan`, porque Qwen ya tiene
smokes live acotados y la siguiente validacion de riesgo es medir calidad/costo
en evals hosted antes de streaming, dashboards, rerank live o persistencia de
conversaciones.

## M8 Hosted evals

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-20-m8-live-provider-evals-plan/`: define
  evals hosted opt-in sobre las suites versionadas de M6 y el runtime de
  providers de M7, con presupuesto maximo de corrida, reportes JSON de
  calidad/usage/costo y Qwen live separado del gate offline obligatorio.

Spec canonica:

- `openspec/specs/hosted-evals/spec.md`

Secuencia entregada:

1. `m8-live-provider-evals-plan`: completo en branch de planificacion. Crea el
   change OpenSpec que delimita hosted evals antes de dashboards, streaming,
   rerank live o tuning automatico.
2. `m8-hosted-eval-contract`: completo. Define modo `offline`/`hosted`,
   modelos de reporte provider usage/cost, presupuesto maximo de corrida,
   validacion de credenciales Qwen y errores estables antes de conectar
   runners live.
3. `m8-live-retrieval-eval-runner`: completo. Ejecuta retrieval evals hosted
   con el provider de embeddings inyectado, materializando evidence y queries
   con el mismo provider/modelo y adjuntando provider usage/cost al reporte.
4. `m8-live-chat-eval-runner`: completo. Ejecuta chat evals hosted con runner
   y provider de embeddings inyectados, reutilizando `ChatService`, retrieval
   tool y validacion de citations, y adjuntando provider usage/cost al reporte.
5. `m8-evals-cli-hosted-mode`: completo. Agrega
   `adaptive-rag evals run <suite> --mode hosted --max-cost-usd <value>` con
   JSON extendido, validacion de credenciales Qwen y tracker compartido entre
   embeddings/chat para reportar usage/cost de la corrida.
6. `m8-quality-gate`: completo. Valida tests, lint, types, specs, evals
   offline y smokes hosted Qwen opcionales con `.env` local; archiva el change
   M8 y publica la spec canonica `hosted-evals`.

Continuacion: M8 deja listo el harness para medir calidad/costo de providers
live. La siguiente decision recomendada es abrir un change OpenSpec para M9 de
calidad de retrieval/rerank, usando hosted evals para comparar mejoras antes de
dashboards, LLM-as-judge, streaming, persistencia de conversaciones o tuning
automatico.

## M9 Retrieval quality/rerank

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-20-m9-retrieval-quality-rerank-plan/`:
  define mejoras de calidad de retrieval con rerank opt-in sobre candidatos
  dense ya filtrados, preservando dense como default y usando hosted evals
  para comparar calidad, usage y costo.

Secuencia entregada:

1. `m9-retrieval-quality-rerank-plan`: completo en branch de planificacion.
   Crea el change OpenSpec que delimita rerank antes de lexical/RRF,
   dashboards, LLM-as-judge, streaming o tuning automatico.
2. `m9-rerank-provider-contract`: completo. Define contratos
   provider-neutral, fake deterministic default, settings/factory runtime para
   fake o Qwen sin llamadas live, errores estables y wiring de budget/price
   catalog antes de tocar HTTP live.
3. `m9-live-qwen-rerank-provider`: completo. Implementa el HTTP client Qwen
   `qwen3-rerank`, parsing de `output.results`, usage/cost, budget guard,
   timeouts/retries y smoke CLI separado.
4. `m9-retrieval-rerank-service`: completo. Integra rerank opcional en
   `RetrievalService` despues de dense candidate generation y filtros,
   preservando default dense y citations.
5. `m9-rerank-api-cli-surface`: completo. Expone knobs acotados de rerank en
   API/CLI sin cambiar el default dense ni construir providers de rerank cuando
   no se habilita.
6. `m9-rerank-hosted-evals`: completo. Compara dense baseline vs reranked
   retrieval en reportes hosted con calidad, `comparison_metrics`, usage y
   costo, y agrega fixture smoke manual.
7. `m9-quality-gate`: completo. Valida tests, lint, types, specs, smoke live
   `providers rerank-smoke`, hosted eval Qwen reranked con SQLite temporal,
   archiva el change y publica `openspec/specs/retrieval-quality/spec.md`.

Decision: rerank fue antes de lexical/RRF porque reutiliza el pipeline dense y
el runtime de providers existente con menor blast radius. La siguiente decision
recomendada es abrir un change OpenSpec para M10 que defina objetivos de
calidad, datasets de eval mas amplios y criterios para decidir si lexical/RRF
o tuning adicional justifican el siguiente incremento.

## M10 Retrieval eval datasets y decision gates

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-20-m10-retrieval-eval-datasets-plan/`:
  define ampliacion de
  suites de retrieval, metricas por caso y decision gates antes de agregar
  lexical/RRF, sparse retrieval o tuning automatico.

Secuencia entregada:

1. `m10-retrieval-eval-datasets-plan`: completo en branch de planificacion.
   Crea el change OpenSpec que delimita M10 como medicion y decision gates
   antes de nuevos algoritmos de ranking.
2. `m10-eval-case-metrics`: completo. Agrega `case_metadata` acotada por caso,
   la serializa en reportes y expone `missing_count` en retrieval evals.
3. `m10-retrieval-dataset-pack`: completo. Agrega una fixture offline
   representativa para exact match, paraphrase, distractors, metadata filters,
   multi-evidence y casos donde rerank ayuda o no debe cambiar el resultado.
4. `m10-rerank-ab-reporting`: completo. Agrega `comparison_cases` por caso,
   improvement/tie/regression counts y delta promedio de best-rank para
   comparar dense vs rerank.
5. `m10-decision-gate-docs`: completo. Documenta criterios para abrir o
   rechazar lexical/RRF, sparse retrieval y tuning de candidate limits con
   evidencia de evals, regresiones, costo/latencia, filtros y citations.
6. `m10-quality-gate`: completo. Valida tests, lint, types, specs, smokes CLI
   offline, smoke live `providers rerank-smoke`, hosted eval Qwen reranked con
   SQLite temporal, archiva el change y sincroniza
   `openspec/specs/retrieval-quality/spec.md`.

Decision: M10 mide antes de construir otro algoritmo. La prioridad es evitar
que lexical/RRF o sparse retrieval entren por intuicion cuando todavia falta
evidencia de regresiones, costo, latencia y comportamiento con filtros/citas.

Continuacion: la siguiente decision recomendada es abrir un change OpenSpec
para elegir el primer experimento medible de retrieval: tuning de candidate
limits, lexical/RRF o Qwen sparse retrieval. La opcion recomendada es decidir
con evidencia primero y solo implementar despues de declarar thresholds,
regresiones aceptables, costo/latencia y comportamiento con filtros/citations.

## M11 Retrieval strategy decision

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-20-m11-retrieval-strategy-decision/`:
  decide el primer experimento medible despues de M10. La recomendacion inicial
  fue proceed con tuning de `candidate_limit`; lexical/RRF y Qwen sparse
  retrieval quedaron en hold hasta tener evidencia o documentacion provider
  suficiente.

Secuencia recomendada:

1. `m11-retrieval-strategy-decision`: completo. Crea el change OpenSpec, registra
   decision matrix y actualiza docs de arquitectura/progreso/roadmap.
2. `m11-candidate-limit-eval-matrix`: completo. Define una matriz interna de
   candidate limits sobre suites versionadas, con coverage por `intent` y
   `difficulty` y validacion de limites.
3. `m11-candidate-limit-ab-runner`: completo. Ejecuta dense baseline una vez,
   compara varios `candidate_limit` reranked contra ese baseline y serializa
   filas estables de quality/cost/regressions con conteos por metadata.
4. `m11-candidate-limit-api-cli-surface`: evaluado y mantenido en hold. La
   evidencia A/B offline mejora el hit rate agregado con `candidate_limit=8`,
   pero mantiene una regresion en `distractor-alpha-release-notes`, por lo que
   no justifica presets ni superficie nueva en M11.
5. `m11-quality-gate`: completo. Valida tests, lint, types y OpenSpec; ejecuta
   smokes hosted Qwen opt-in con `.env` local; archiva el change y publica
   `openspec/specs/retrieval-quality/spec.md`.

Decision: candidate tuning va primero porque tiene menor blast radius y mide si
el problema real es candidate reach/costo antes de agregar indexes o providers.
Lexical/RRF requiere fallos lexicales medidos. Qwen sparse requiere verificar
docs actuales de DashScope/Qwen, storage, reindex y costo antes de codificar.

Continuacion: M11 cierra candidate tuning sin promover presets ni defaults
nuevos. La siguiente decision abierta es M12, enfocada en ampliar evidencia de
retrieval sobre distractors y lexical misses antes de proponer lexical/RRF,
sparse retrieval o nuevos providers.

## M12 Retrieval evidence expansion

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-20-m12-retrieval-evidence-expansion/`

Secuencia recomendada:

1. `m12-retrieval-evidence-expansion`: activo en branch de planificacion. Crea
   el change OpenSpec que delimita M12 como expansion de evidencia, sin tocar
   ranking productivo, providers, storage ni defaults.
2. `m12-evidence-case-taxonomy`: completo. Agrega `risk_family` opcional y
   estricto en `case_metadata`, lo serializa en reportes y permite agrupar la
   matrix de candidate limits por familia de riesgo con fallback
   `uncategorized`.
3. `m12-distractor-lexical-dataset-pack`: completo. Amplia
   `retrieval-dataset-pack` a 16 evidencias y 10 casos con lexical misses,
   identifiers exactos, distractors semanticos y `risk_family` versionada.
4. `m12-evidence-gap-reporting`: completo. Extiende el reporte A/B de
   candidate limits con conteos por `risk_family` y serializa
   `comparison_cases` con regresiones primero.
5. `m12-strategy-decision-refresh`: completo. Ejecuta la suite ampliada con el
   runner A/B offline y documenta la decision matrix: dense default `proceed`,
   candidate tuning presets/defaults `no-go`, lexical/RRF `hold` y Qwen sparse
   retrieval `hold`.
6. `m12-quality-gate`: completo. Valida tests, lint, types, specs, evals
   relevantes, archiva el change y publica la spec canonica actualizada de
   `retrieval-quality`.

Decision: M12 midio antes de construir. Dense retrieval sigue como default.
Candidate tuning presets/defaults quedaron en `no-go`; lexical/RRF y Qwen
sparse retrieval quedaron en `hold`.

Continuacion: no agregar algoritmos de retrieval todavia. La siguiente prioridad
seleccionada es M13 Chat audit trail, una necesidad fuera de ranking para dejar
sesiones, mensajes, tool calls, retrieval runs, citations y usage/cost en un
registro durable antes de streaming, dashboards o historial.

## M13 Chat audit trail

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-21-m13-chat-audit-trail/`

Spec canonica:

- `openspec/specs/chat-audit-trail/spec.md`

Secuencia recomendada:

1. `m13-chat-audit-trail`: planificacion completa. Creo el change OpenSpec
   que delimita M13 como persistencia durable de chat sin streaming, historial,
   dashboards ni cambios de ranking.
2. `m13-audit-schema`: completo en branch de implementacion. Agrega migracion
   Alembic y modelos SQLAlchemy para sesiones, mensajes, tool calls, retrieval
   runs, retrieved chunks y provider usage.
3. `m13-audit-repositories`: completo en branch de implementacion. Agrega
   repositories con aislamiento por proyecto, transiciones de status y
   saneamiento de metadata sin secretos.
4. `m13-chat-service-audit-wiring`: completo en branch de implementacion.
   Integra la escritura del audit trail en `ChatService`, preservando
   validacion de citations y fakes deterministas.
5. `m13-api-cli-audit-surface`: completo en branch de implementacion. Hace que
   API/CLI persistan el audit trail por defecto y expongan solo metadata minima
   como `session_id` si el contrato lo requiere.
6. `m13-provider-usage-linking`: completo en branch de implementacion. Vincula
   usage/cost de providers al contexto durable disponible sin romper runners
   offline.
7. `m13-quality-gate`: completo en branch de implementacion. Valida tests,
   lint, types, specs y smoke CLI.
8. `m13-closeout`: completo. Archiva el change OpenSpec, publica la spec
   canonica `chat-audit-trail` y reconcilia `docs/progress.md` y este roadmap
   despues del merge de PR #69.

Decision: M13 va antes de streaming SSE, dashboards e historial porque esas
superficies necesitan una fuente durable para reproducir mensajes, tool calls,
retrieval context, citations, errores y usage/cost. M13 no cambia retrieval
productivo ni agrega algoritmos nuevos.

Continuacion: M13 deja audit trail durable pero todavia no expone una
superficie publica para consultar sesiones o historial. La siguiente opcion
recomendada es abrir un change M14 para lectura/historial de chat aislado por
proyecto, antes de streaming SSE o dashboards, porque reduce el riesgo de esas
superficies al fijar primero el contrato de consulta.

## M14 Chat history/read surface

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-21-m14-chat-history-read-surface/`

Spec canonica:

- `openspec/specs/chat-history/spec.md`

Secuencia recomendada:

1. `m14-chat-history-read-surface`: completo. Crea el
   change OpenSpec que delimita M14 como superficie read-only de listado y
   detalle de sesiones de chat sobre el audit trail durable de M13.
2. `m14-chat-history-repository-read-models`: completo. Agrega read models y
   queries compartidas para resumen/detalle de sesiones, con aislamiento por
   proyecto, filtros de status, limite acotado y orden deterministico.
3. `m14-chat-history-api`: completo. Agrega
   `GET /projects/{project_id}/chat/sessions` y
   `GET /projects/{project_id}/chat/sessions/{session_id}` con schemas HTTP
   estables, validacion de opciones invalidas y respuesta 404 para sesiones
   inexistentes o cross-project.
4. `m14-chat-history-cli`: completo. Agrega
   `adaptive-rag chat sessions list` y `adaptive-rag chat sessions show` con
   salida JSON estable equivalente a la API, con filtros/cursor de listado,
   detalle auditable y error estable para sesiones inexistentes o cross-project.
5. `m14-quality-gate`: completo. Valida tests, lint, types, specs y smokes CLI
   relevantes; archiva M14 y publica la spec canonica `chat-history`.

Decision: M14 va antes de frontend, streaming SSE y dashboards porque fija el
contrato de lectura que esas superficies consumiran. M14 no re-ejecuta chat, no
muta audit trail, no agrega UI y no cambia retrieval productivo.

Continuacion: M14 deja listo el contrato backend para una primera UI de chat e
historial. La siguiente decision recomendada es abrir un change OpenSpec nuevo
para frontend/UI inicial sobre `POST /chat` y `chat-history`, manteniendo
streaming SSE, dashboards y replay fuera de alcance hasta que la experiencia
base este definida.

## M15 Chat frontend inicial

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-21-m15-chat-frontend-plan/`

Spec canonica:

- `openspec/specs/chat-frontend/spec.md`

Secuencia recomendada:

1. `m15-chat-frontend-plan`: completo. Crea el change OpenSpec que delimita
   M15 como primera UI de chat e historial sobre los contratos existentes de M5
   y M14.
2. `m15-frontend-scaffold`: completo. Crea `frontend/` con
   React/TypeScript/Vite, `pnpm`, scripts de dev/build/lint/test/typecheck,
   `.env.example`, README local y lockfile.
3. `m15-chat-api-client`: completo. Agrega Vitest y cliente `fetch` tipado
   para `POST /chat`, listado de sesiones y detalle read-only, con errores HTTP
   estructurados y tests deterministas sin backend live.
4. `m15-chat-workspace-ui`: completo. Conecta el shell React con el cliente API
   para enviar preguntas, mostrar answer, `session_id`, citations y tool calls
   minimas, y refrescar sesiones recientes despues de respuestas exitosas.
5. `m15-chat-history-ui`: completo. Agrega refresh manual de sesiones por
   proyecto, seleccion de sesion y detalle read-only de mensajes, tool calls,
   retrieval runs, citations y provider usage.
6. `m15-quality-gate`: completo. Valida frontend, Python y OpenSpec; archiva
   el change M15 y publica la spec canonica `chat-frontend`.

Decision: M15 va antes de streaming SSE, dashboards y replay porque primero
necesitamos una app operativa que consuma los contratos cerrados sin ampliar la
superficie backend. M15 no cambia retrieval productivo, providers, rerank,
CLI ni API backend salvo que un slice posterior descubra una brecha de contrato
que deba pasar por OpenSpec.

Continuacion: M15 deja una app frontend operativa para `POST /chat` e historial
read-only. La siguiente decision recomendada es abrir un change M16 para
streaming de chat por SSE, porque mejora la experiencia de respuestas largas
sobre la UI existente y debe fijar contrato, fallback y persistencia antes de
dashboards, replay o auth final.

## M16 Chat streaming SSE

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-21-m16-chat-streaming-sse/`

Spec canonica:

- `openspec/specs/chat-streaming/spec.md`

Secuencia recomendada:

1. `m16-chat-streaming-sse`: completo. Crea el change OpenSpec que delimita
   M16 como streaming de chat por SSE sobre los contratos de M5, M13, M14 y
   M15.
2. `m16-streaming-event-contract`: completo. Agrega tipos de eventos,
   factories, serializer SSE determinista y tests sin endpoint HTTP.
3. `m16-chat-service-streaming`: completo. Agrega `ChatService.stream`
   compartiendo validacion, audit trail, retrieval tool, citations y provider
   usage con el flujo no streaming.
4. `m16-chat-streaming-api`: completo. Agrega
   `POST /projects/{project_id}/chat/stream` con `text/event-stream`,
   validacion 422 antes de abrir stream, eventos SSE serializados y cierre
   estable con `final` o `error`.
5. `m16-chat-streaming-frontend-client`: completo. Agrega cliente `fetch`
   streaming, parser SSE para chunks partidos/agrupados, `AbortController`,
   errores estructurados y fallback al flujo no streaming.
6. `m16-chat-streaming-ui`: completo. Integra respuesta parcial,
   `session_started`, tool calls, cancelacion, fallback y refresh de historial
   despues de `final`.
7. `m16-quality-gate`: completo. Valida frontend, Python y OpenSpec; archiva
   M16 y publica la spec canonica `chat-streaming`.

Decision: M16 usa SSE por `POST` consumido con `fetch` streaming porque el
contrato de chat necesita body JSON para mensaje, limite y filtros. `POST /chat`
queda como fallback obligatorio. M16 no agrega WebSockets, dashboards, replay,
auth final, ni cambios de retrieval/rerank/providers.

Continuacion: M16 deja streaming SSE operativo en backend y frontend, con
fallback no streaming y audit trail durable. La siguiente opcion seleccionada es
M17 para observability de chat/costo-latencia sobre sesiones y `provider_usage`,
antes de replay, auth final o nuevas estrategias de retrieval, porque el
producto ya puede responder y persistir conversaciones y ahora necesita
visibilidad operativa de costo, latencia, errores y volumen.

## M17 Chat observability y costo-latencia

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-21-m17-chat-observability/`

Spec canonica:

- `openspec/specs/chat-observability/spec.md`

Secuencia recomendada:

1. `m17-chat-observability`: completo. Crea el change OpenSpec que delimita M17
   como observability local-first de chat, costo y latencia sobre audit trail
   existente, con API/CLI read-only y sin dashboard avanzado.
2. `m17-observability-read-models`: completo. Agrega read models y repository
   methods para resumir sesiones, provider usage, latencias y errores por
   proyecto, con filtros de status/fecha y calculos portables.
3. `m17-observability-api`: completo. Agrega
   `GET /projects/{project_id}/chat/observability/summary` con JSON estable,
   validacion de filtros e aislamiento por proyecto.
4. `m17-observability-cli`: completo. Agrega
   `adaptive-rag chat observability summary` con salida JSON equivalente a la
   API y filtros equivalentes.
5. `m17-quality-gate`: completo. Valida Python, OpenSpec y docs; archiva M17
   y publica la spec canonica `chat-observability`.

Decision: M17 empieza por API/CLI porque fija el contrato de agregados antes de
invertir en UI. Usa datos existentes (`chat_sessions`, `tool_calls`,
`retrieval_runs` y `provider_usage`) y no agrega nuevas tablas inicialmente.
M17 no agrega dashboard avanzado, frontend, OpenTelemetry, exporters hosted,
replay, auth final ni cambios de retrieval/rerank/providers.

Continuacion: el siguiente milestone seleccionado es M18 Neo4j graph DB
decision. Debe empezar por decision matrix y contrato routeable antes de agregar
dependencias, adapter live, indexer o retrieval graph.

## M18 Neo4j graph DB decision

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-22-m18-neo4j-graph-db-decision/`

Objetivo:

- Evaluar e integrar Neo4j como graph DB opcional para retrieval graph,
  manteniendo `pgvector`/dense retrieval como baseline y Postgres como fuente
  durable principal del dominio.

Condiciones del milestone:

- La integracion debe ser routeable desde settings, con `graph_store=disabled`
  como default y una opcion explicita `graph_store=neo4j`.
- Retrieval graph debe poder habilitarse/deshabilitarse sin migrar datos
  primarios ni romper API/CLI existentes.
- Neo4j debe tener una ruta local completamente viable, por ejemplo Docker o
  Neo4j Desktop, y una ruta managed/externa equivalente, como Neo4j Aura.
- El grafo debe tratarse como indice derivado y reconstruible desde Postgres,
  no como unica fuente de verdad.
- La primera version debe preservar aislamiento por proyecto, filtros de
  metadata, citations y auditoria de retrieval.
- La integracion no debe depender de providers hosted: debe funcionar con el
  runtime Qwen/local ya definido o con fakes deterministas en tests.
- El default productivo no cambia hasta que evals versionadas demuestren mejoras
  sin regresiones criticas de calidad, costo, latencia, filtros o citations.

Secuencia recomendada:

1. `m18-neo4j-graph-db-decision`: completo. Documenta el plan, crea la capacidad
   `graph-store` y fija la secuencia de M18 sin tocar codigo productivo.
2. `m18-graph-db-decision-matrix`: completo. Selecciona Neo4j como primer
   backend live opt-in; mantiene Memgraph y FalkorDB en `hold`, Kuzu en
   `no-go` para el backend routeable de M18 y no-op como fallback de evals.
   Tambien fija que Postgres conserve la fuente canonica y readiness/backfill
   por proyecto para reconstruir Neo4j si estuvo disabled.
3. `m18-graph-store-contract`: completo. Define `graph_store=disabled|neo4j`,
   contrato `GraphStore`, health check, errores estables, fakes offline y
   `graph_projections` en Postgres para readiness/backfill por proyecto, sin
   adapter live ni cambios de retrieval.
4. `m18-neo4j-adapter-and-health`: completo. Agrega dependencia `neo4j>=6.0`,
   adapter `Neo4jGraphStore`, factory `get_graph_store(...)`, validacion de
   URI/auth y health check con `verify_connectivity()` y errores estables sin
   exponer secretos.
5. `m18-neo4j-indexer`: completo. Materializa nodos/relaciones derivados
   desde proyectos, sources, documents, document versions, chunks y metadata con
   backfill idempotente por `project_id`.
6. `m18-graph-retrieval-route`: completo. Agrega `strategy=dense|graph` en
   retrieval API/CLI, consulta graph DB solo con proyeccion `ready`, rehidrata
   citations desde Postgres y vuelve a dense con `fallback_reason` estable
   cuando graph no puede usarse.
7. `m18-evals-quality-gate`: completo. Agrega un gate dense-vs-graph con
   metricas de hit rate, best-rank delta, regresiones, filtros, citation
   coverage y costo provider incremental. La decision queda `hold_default`:
   graph retrieval sigue opt-in y dense sigue como default.

Decision: Neo4j avanza como candidato principal para una integracion graph DB
opcional, no como requisito del stack base. M18 queda cerrado con Postgres como
fuente durable, Neo4j como indice derivado opt-in y `dense` como default.

## M19 Graph live ops evidence

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-22-m19-graph-live-ops-plan/`

Objetivo:

- Medir y operar Neo4j live como indice derivado opt-in antes de cualquier
  promocion de graph retrieval, manteniendo `strategy=dense` como default y
  Postgres como fuente durable.

Condiciones del milestone:

- La ruta local debe ser verificable con Docker o Neo4j Desktop.
- La ruta managed debe aceptar URI cifrada `neo4j+s://...` y secretos por
  settings/env, sin imprimir credenciales.
- Backfill/reindex debe ser idempotente, acotado por `project_id` y gobernado
  por estados de readiness en Postgres.
- Retrieval graph live solo puede correr con proyeccion `ready` y debe conservar
  fallback dense con razon estable.
- La evidencia debe separar calidad, latencia, fallback, duracion de
  backfill/reindex, error codes y costo operacional graph declarado.
- M19 no puede promover graph como default. Si la evidencia justifica avanzar,
  debe cerrar como `limited_experiment` y abrir un milestone posterior de
  rollout/defaults.

Secuencia recomendada:

1. `m19-graph-live-ops-plan`: completo. Crea el change OpenSpec, documenta el
   scope de evidencia/operacion live y actualiza progress/roadmap/arquitectura.
2. `m19-neo4j-local-managed-harness`: completo. Documenta setup local/managed y
   agrega `adaptive-rag graph neo4j-smoke` como smoke opt-in de
   settings/connectivity con errores estables y salida JSON sin secretos.
3. `m19-graph-backfill-reindex-ops`: completo. Agrega comandos operativos para
   backfill/reindex por proyecto, con transiciones `pending_backfill`,
   `indexing`, `ready` y `failed`, reporte JSON de duracion/error code y
   conteos del payload materializado.
4. `m19-graph-live-retrieval-smoke`: completo. Agrega
   `adaptive-rag graph retrieval-smoke` para ejecutar `strategy=graph` con
   proyeccion `ready`, filtros, citations, latencia y salida no cero ante
   fallback o ausencia de hits graph.
5. `m19-graph-live-evidence-report`: completo. Agrega
   `adaptive-rag evals graph-live-evidence` para reportar calidad
   dense-vs-graph, latencia, fallback, errores, duracion de backfill/reindex y
   costo operacional declarado desde artefactos JSON previos.
6. `m19-quality-gate`: completo. Valida Python/OpenSpec, archiva el change y
   publica los requisitos de evidencia operacional en la spec canonica
   `graph-store`.

Decision: `hold_default`. El repo ya tiene harness, backfill/reindex, smoke de
retrieval graph y reporte de evidencia, pero el gate local no tuvo entorno
Neo4j live configurado para demostrar latencia/costo operacional concluyente.
`dense` sigue como default; Neo4j live sigue opt-in.

Continuacion: graph rollout queda pausado hasta contar con Neo4j live y un
proyecto/dataset controlado para producir evidencia real. Sin ese entorno, el
siguiente bloque seleccionado es M20 Chat observability dashboard sobre la
superficie M17 ya estable.

## M20 Chat observability dashboard

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-22-m20-chat-observability-dashboard-plan/`

Objetivo:

- Exponer un dashboard frontend read-only de observability de chat para revisar
  sesiones, costo, latencia, errores, provider usage y salud reciente usando
  APIs publicas existentes.

Condiciones del milestone:

- El dashboard debe empezar consumiendo
  `GET /projects/{project_id}/chat/observability/summary`.
- Puede reutilizar `GET /projects/{project_id}/chat/sessions` para sesiones
  recientes.
- Las tarjetas y tablas deben etiquetar metricas segun la derivacion real del
  contrato; no se debe inventar p95 global desde p95 por grupos.
- Cualquier extension backend debe ser backward-compatible, derivada de tablas
  existentes y sin nuevas tablas/materialized views en el primer slice.
- La UI no debe exponer mensajes completos, respuestas completas, provider
  payloads, prompts, API keys ni secretos.
- M20 no cambia retrieval, rerank, providers, streaming ni graph defaults.

Secuencia recomendada:

1. `m20-chat-observability-dashboard-plan`: completo. Crea el change OpenSpec,
   documenta el layout hibrido aprobado y modifica `chat-observability` y
   `chat-frontend`.
2. `m20-observability-frontend-client`: completo. Agrega tipos y cliente API
   para el summary M17, con tests de query params y errores.
3. `m20-observability-dashboard-shell`: completo. Agrega vista de observability
   con filtros, refresh y metric cards.
4. `m20-observability-breakdowns`: completo. Agrega breakdowns de
   status/errores, provider usage table y session health table.
5. `m20-observability-summary-shape`: no necesario; el summary M17 cubrio los
   breakdowns sin extension backend.
6. `m20-quality-gate`: completo. Valida frontend/Python/OpenSpec, smokes CLI,
   archiva el change M20 y publica las specs canonicas `chat-frontend` y
   `chat-observability`.

Decision: proceed con frontend-first. M20 captura valor de producto sobre el
audit trail y observability ya implementados, mientras graph rollout queda en
hold hasta tener evidencia live concluyente.

Continuacion: M20 queda cerrado. La siguiente tarea debe abrir un nuevo change
OpenSpec desde `main` para el proximo milestone antes de implementar.

## M21 V1 core/readiness

Estado: cerrado el 2026-06-22.

Change archivado:

- `openspec/changes/archive/2026-06-22-m21-v1-release-readiness-plan/`

Objetivo:

- Convertir M1-M20 en un core local-first demostrable, con alcance explicito,
  deferrals auditable, release package local-first, demo y reporte reproducible.
  M22 redefine posteriormente que esto no basta para llamar terminado a v1.

Condiciones del milestone:

- M21 no debe agregar runtime features en el PR de planificacion.
- El alcance v1.0 debe reconciliar `docs/architecture/v1-design.md` contra
  specs canonicas y decisiones M10-M20.
- Cada item original de v1 debe quedar clasificado como `in_v1`,
  `defer_post_v1` o `blocked`.
- Dense retrieval sigue como default; rerank queda opt-in y medible.
- Lexical/RRF, Qwen sparse, graph defaults, voz, MCP server, auth multi-user y
  PDF/Office no entran por inercia.
- El release package debe ser local-first: API, worker y Postgres/pgvector.
- La evidencia final debe incluir README/demo y reporte reproducible de
  evals/costo/latencia.

Resultado:

1. `m21-v1-scope-reconciliation`: completo. `v1-design.md` separa `in_v1` y
   `defer_post_v1`, con OpenSpec como autoridad.
2. `m21-release-package-local-stack`: completo. `Dockerfile`, `compose.yaml`,
   `.env.example` y runbook local cubren API, worker project-scoped y
   Postgres/pgvector.
3. `m21-portfolio-demo-and-report`: completo. README y runbook documentan demo
   offline reproducible con fixtures de evals y providers `fake`.
4. `m21-release-quality-gate`: completo. Frontend/Python/OpenSpec/compose y
   smokes CLI pasaron, y M21 quedo archivado.

Decision: M21 cierra con recorte conservador del core. El sistema queda
demostrable local-first, pero no como producto v1 terminado. Lexical/RRF, Qwen
sparse, graph defaults y features aspiracionales no se reabren sin
evidencia/OpenSpec nuevo. Las nuevas surfaces de authoring ya no son
"post-v1" por defecto: M22 las reclasifica como gap de producto para una v1
real.

## M22 V1 product scope reset

Estado: cerrado el 2026-06-23.

Change archivado:

- `openspec/changes/archive/2026-06-23-m22-v1-product-scope-reset/`

Specs canonicas:

- `openspec/specs/v1-product-completion/spec.md`
- `openspec/specs/v1-release-readiness/spec.md`

Objetivo:

- Redefinir v1 como producto local-first single-user terminado, no como release
  de portafolio del core M1-M21.

Condiciones del milestone:

- M21 queda como evidencia de core/pre-v1 y no autoriza tag/manual release
  v1.0.
- El porcentaje de v1 debe recalcularse contra backlog de producto terminado,
  no contra la checklist de release package M21.
- El producto v1 debe permitir crear proyecto, agregar sources, ejecutar
  ingestion, ver estado de jobs, consultar con citations y operar errores desde
  superficies publicas documentadas.
- La demo final debe usar datos propios o sample inputs creados por las
  superficies publicas; no puede depender de fixtures internas como happy path
  principal.
- Dense retrieval sigue como default; rerank, Qwen hosted y Neo4j/graph siguen
  opt-in. Lexical/RRF, Qwen sparse, graph default, auth multi-user, PDF/Office,
  voice y MCP no entran por inercia.

Secuencia recomendada:

1. `m22-v1-product-scope-reset`: completo. Corrige docs y OpenSpec para
   bloquear una release v1 prematura.
2. `m23-product-authoring-surface`: completo. Crear/listar/ver projects y
   sources desde API, CLI y frontend.
3. `m24-ingestion-ops-surface`: completo. Ejecutar ingestion end-to-end y
   exponer job state, failure reasons y retry/dead-letter.
4. `m25-first-run-onboarding`: completo. Setup local, migraciones, seed/demo
   y guia para datos propios.
5. `m26-v1-product-quality-gate`: completo. Demo final con datos propios,
   docs, smokes y gate de release real.

Continuacion: M26 queda como cierre del backlog de producto v1 local-first
single-user. La siguiente decision no es agregar features por defecto, sino
mergear el gate, reejecutar la evidencia desde `main` y decidir manualmente tag
o GitHub release v1.0.

## M23 Product authoring surface

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-23-m23-product-authoring-surface/`

Spec canonica:

- `openspec/specs/product-authoring-surface/spec.md`

Objetivo:

- Permitir que un usuario local cree/lista/vea projects y sources desde
  superficies publicas, sin SQL manual ni fixtures internas.

Condiciones del milestone:

- La surface publica debe cubrir API, CLI y frontend para projects y sources.
- Crear project usa `embedding_mode = dense` como default publico; `dense_sparse`
  sigue reservado hasta evidencia/OpenSpec nuevo.
- Crear source soporta `markdown`, `text`, `txt` y `url`, que son los tipos que
  el pipeline de ingestion ya entiende.
- Para sources text-like, el contenido se guarda en `extra_metadata.content`.
- Crear source no encola `ingest_source`, no crea documents, no crea chunks y no
  llama providers. Ingestion/job state queda para M24.
- La UI debe ser una surface de trabajo compacta integrada con chat/history/
  observability, no una landing page.

Secuencia recomendada:

1. `m23-product-authoring-surface`: completo. Crea el plan OpenSpec y documenta
   los contratos.
2. `m23-authoring-api-contract`: completo. Agrega schemas/routes API y ajustes
   minimos de repositories para crear/listar/ver projects y sources.
3. `m23-authoring-cli`: completo. Agrega comandos JSON de projects/sources.
4. `m23-authoring-frontend`: completo. Agrega cliente y UI compacta de
   projects/sources.
5. `m23-quality-gate`: completo. Valida frontend/backend/OpenSpec y archiva
   M23.

Continuacion: abrir `m24-ingestion-ops-surface`, para ejecutar ingestion
explicitamente desde superficies publicas, mostrar job state y permitir retry/
dead-letter sin depender de SQL manual.

## M24 Ingestion ops surface

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-23-m24-ingestion-ops-surface/`

Spec canonica:

- `openspec/specs/ingestion-ops-surface/spec.md`

Objetivo:

- Permitir que un usuario local procese sources existentes desde superficies
  publicas, vea job state/error y pueda reintentar fallos retryable sin SQL
  manual.

Condiciones del milestone:

- La surface publica debe cubrir API, CLI y frontend para enqueue/list/show/
  run-next/retry de ingestion jobs.
- Crear source sigue sin ejecutar ingestion automaticamente; el disparo es
  explicito y observable.
- `run-worker --once` y la API de run-next deben reportar `processed`,
  `blocked` o `idle` de forma estable.
- Jobs `blocked` y `dead_letter` se pueden reencolar limpiando error/lease y
  dejando evento `retried`.
- La UI debe mantener Authoring como superficie de trabajo compacta, con
  controles por source y panel de jobs.

Secuencia recomendada:

1. `m24-ingestion-ops-surface`: completo. Crea el plan OpenSpec y documenta
   contratos de ingestion ops.
2. `m24-backend-api-contract`: completo. Agrega repository/ops/routes/schemas y
   reporte observable de blocked jobs.
3. `m24-cli-ops`: completo. Agrega comandos JSON de jobs y estabiliza
   `run-worker --once`.
4. `m24-authoring-ingestion-ui`: completo. Agrega cliente y controles compactos
   de enqueue/run/status/retry.
5. `m24-quality-gate`: completo. Valida backend/frontend/OpenSpec y archiva
   M24.

Continuacion: abrir `m25-first-run-onboarding`, para cerrar setup local,
migraciones, seed/demo y guia de datos propios sobre las superficies publicas
M23/M24 antes del gate final de v1.

## M25 First-run onboarding

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-23-m25-first-run-onboarding/`

Spec canonica:

- `openspec/specs/first-run-onboarding/spec.md`

Objetivo:

- Permitir que un usuario local llegue desde una instalacion inicial hasta una
  respuesta de chat con citations usando datos sample o propios creados por
  superficies publicas.

Condiciones del milestone:

- El runbook debe cubrir dependencias, Postgres, migraciones y smoke default.
- El comando `adaptive-rag first-run smoke` debe crear project/source, ejecutar
  ingestion, chunking, embeddings fake y chat con citations.
- La salida debe ser JSON machine-readable con ids, job status, conteos,
  answer, `citation_count` y siguientes comandos.
- Qwen, rerank hosted y Neo4j deben quedar marcados como opt-in, no como
  requisito del camino default.
- README debe apuntar a `docs/first-run.md` como primera ruta de producto local.

Secuencia recomendada:

1. `m25-first-run-onboarding`: completo. Crea el plan OpenSpec y documenta el
   contrato de primera corrida.
2. `m25-first-run-cli-smoke`: completo. Agrega servicio/CLI para crear datos,
   ingerir, indexar y consultar con citations.
3. `m25-first-run-runbook`: completo. Agrega `docs/first-run.md` y actualiza
   README con el camino default.
4. `m25-quality-gate`: completo. Valida backend/frontend/OpenSpec y archiva
   M25.

Continuacion: M26 convierte la primera corrida en evidencia final de release
real con demo, smokes, docs y decision v1.0.

## M26 V1 product quality gate

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-23-m26-v1-product-quality-gate/`

Specs canonicas:

- `openspec/specs/v1-product-completion/spec.md`
- `openspec/specs/v1-release-readiness/spec.md`

Objetivo:

- Convertir el first-run local en evidencia final de producto v1 con una
  decision machine-readable de release.

Condiciones del milestone:

- El comando `adaptive-rag v1 quality-gate` debe ejecutar el flujo publico de
  project/source, ingestion, chunking, embeddings fake y chat con citations.
- La salida debe incluir `release_decision`, criterios de release, evidencia
  `first_run`, job state, conteos de indexing, citation count, deferrals y
  nota de accion manual.
- `ready_for_v1_0` no crea tag ni GitHub release automatico.
- Qwen hosted, rerank hosted, Neo4j/graph, auth multi-user, PDF/Office, voice,
  MCP server y hosted observability siguen fuera del default salvo nuevo
  OpenSpec.

Secuencia recomendada:

1. `m26-v1-product-quality-gate`: completo. Crea el plan OpenSpec y documenta
   el contrato final de gate v1.
2. `m26-quality-gate-cli`: completo. Agrega `adaptive-rag v1 quality-gate` con
   reporte JSON, criterios de release y soporte `--output`.
3. `m26-release-runbook`: completo. Agrega `docs/v1-quality-gate.md` y
   actualiza README.
4. `m26-quality-gate`: completo. Valida backend/frontend/OpenSpec y archiva
   M26.

Continuacion: abrir M27 para nuevo alcance post-v1 si se decide preparar
capacidades avanzadas de retrieval antes del frontend polish.

## M27 Post-v1 retrieval expansion

Estado: completo.

Change archivado:

- `openspec/changes/archive/2026-06-23-m27-retrieval-expansion-plan/`

Objetivo:

- Dejar listas capacidades avanzadas de retrieval antes de pulir frontend, sin
  cambiar el default `dense` hasta contar con evidencia comparativa.

Condiciones del milestone:

- M27 no implementa runtime retrieval; define alcance, secuencia y gates.
- Todas las capacidades nuevas empiezan opt-in.
- `dense` sigue como default y fallback hasta que M31 recomiende promocion.
- Frontend polish debe esperar contratos backend estables o excluir los modos
  avanzados del alcance visual.

Secuencia recomendada:

1. `m27-retrieval-expansion-plan`: completo. Crea el OpenSpec post-v1 y fija el
   orden de trabajo.
2. `m28-contextual-retrieval-generated-summaries`: activo. Generar
   `contextual_summary`, reusar `embedding_input_text`/`lexical_input_text` y
   exponer evidencia de indexing contextualizado por first-run.
3. `m29-lexical-retrieval-rrf`: propuesto. Agregar Postgres full-text local y
   RRF preservando filtros, ordering estable y citations.
4. `m30-qwen-sparse-dense-sparse`: propuesto. Verificar docs actuales de Qwen y
   completar storage/scoring/reindex para `dense_sparse` como opt-in.
5. `m31-retrieval-strategy-gate`: propuesto. Comparar dense, contextual dense,
   lexical, sparse, hybrid RRF, graph opt-in y rerank para decidir `promote`,
   `keep_opt_in`, `hold`, `no_go` o `needs_more_data`.

Continuacion: completar M28 y luego abrir M29. La razon es directa: despues de
persistir contexto estable por chunk, lexical/RRF puede reutilizar el mismo
campo de entrada sin inventar una superficie frontend.

## M28 Contextual Retrieval generated summaries

Estado: activo.

Change activo:

- `openspec/changes/m28-contextual-retrieval-generated-summaries/`

Objetivo:

- Generar y persistir `contextual_summary` durante indexing local antes de
  embeddings densos, sin cambiar el default `dense`.

Condiciones del milestone:

- El contextualizer default debe ser local y determinista.
- La pipeline debe ser project-scoped e idempotente.
- `first-run` debe reportar `contextualized_chunk_count` y
  `reused_contextualized_chunk_count`.
- Citations deben seguir saliendo del texto normalizado original, no del
  resumen generado.

Secuencia recomendada:

1. `m28-contextualization-pipeline`: activo. Agrega generador local, pipeline y
   persistencia de summaries.
2. `m28-first-run-reporting`: activo. Wirea first-run y quality gate mediante
   los conteos nuevos.
3. `m28-docs-and-gate`: activo. Actualiza runbooks, valida OpenSpec y deja M28
   listo para archivar.

Continuacion: archivar M28 y abrir M29 para lexical/RRF local.

## Politica para reducir conflictos de merge

- Solo un PR activo debe tocar migraciones Alembic y modelos SQLAlchemy a la vez.
- Abrir branches de repositories o workers solo despues de mergear el PR de schema.
- Mantener ediciones del roadmap en PRs de planificacion o cierre de milestone.
- No duplicar progreso rutinario en `docs/progress-log/`; OpenSpec archive, PRs y git son suficientes para cierres normales.
