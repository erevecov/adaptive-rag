# Roadmap de Adaptive RAG

## Estado actual

- M1 Foundation: completo.
- M2 Dominio y persistencia: completo.
- M3 Ingestion y retrieval: completo.
- M4 Superficie de retrieval: completo.
- M5 Chat/tool calling: completo.
- M6 Evals: planificacion en curso.

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

Estado: planificacion en curso.

Change activo:

- `m6-evals-plan`: define evaluaciones offline de retrieval/chat sobre las
  superficies estables de M4/M5, con datasets versionados, runners
  deterministas, metricas objetivas, reportes JSON y CLI no interactiva.

Secuencia inicial propuesta:

1. `m6-evals-plan`: completo en branch de planificacion. Crea el change
   OpenSpec que delimita evals offline antes de providers live, streaming o
   persistencia de conversaciones.
2. `m6-evals-fixtures-contract`: completo. Crea el paquete
   `adaptive_rag.evals` inicial, modelos de casos/resultados y loader de
   fixtures versionados con validacion estricta.
3. `m6-retrieval-eval-runner`: completo. Ejecuta casos de retrieval contra
   `RetrievalService` con provider fake y metricas top-k/expected chunk.
4. `m6-chat-eval-runner`: siguiente. Ejecutar casos de chat contra
   `ChatService` con runner fake y checks de citations/tool calls.
5. `m6-evals-cli-reporting`: pendiente. Agregar `adaptive-rag evals run` con
   salida JSON, thresholds y exit code estable para CI.
6. `m6-quality-gate`: pendiente. Validar y cerrar el milestone antes de evals
   hosted, dashboards o tuning automatico.

Siguiente tarea recomendada: implementar `m6-chat-eval-runner`, porque retrieval
ya tiene un harness offline reutilizable y el siguiente riesgo es validar
citations, tool calls y ausencia de evidence inventada antes de publicar CLI.

## Politica para reducir conflictos de merge

- Solo un PR activo debe tocar migraciones Alembic y modelos SQLAlchemy a la vez.
- Abrir branches de repositories o workers solo despues de mergear el PR de schema.
- Mantener ediciones del roadmap en PRs de planificacion o cierre de milestone.
- No duplicar progreso rutinario en `docs/progress-log/`; OpenSpec archive, PRs y git son suficientes para cierres normales.
