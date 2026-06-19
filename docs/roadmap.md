# Roadmap de Adaptive RAG

## Estado actual

- M1 Foundation: completo.
- M2 Dominio y persistencia: completo.
- M3 Ingestion y retrieval: siguiente.

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

Estado: planificacion.

Change activo:

- `m3-ingestion-retrieval-plan`: en curso. Define el corte inicial de M3 antes de escribir codigo productivo.

Secuencia inicial propuesta:

1. `m3-ingestion-retrieval-plan`: en curso. Crear el change OpenSpec que delimita los primeros slices de ingestion/retrieval sobre los contratos ya cerrados de M2.
2. `m3-ingestion-pipeline`: completo en branch de implementacion. Conecta sources, documents, document versions, jobs y `URLFetchPolicy` en un flujo de ingestion verificable con fakes, sin chunking ni embeddings.
3. `m3-chunking-baseline`: siguiente. Implementar chunking semantico inicial con offsets reproducibles para citations.
4. `m3-embedding-baseline`: construir inputs de embedding/contexto y persistir embeddings densos usando provider fakes antes de Qwen live.
5. `m3-retrieval-baseline`: implementar retrieval exacto inicial con filtros por proyecto y metadata, basado en datos persistidos por los slices anteriores.
6. `m3-quality-gate`: validar y cerrar el milestone antes de chat/tool calling.

Siguiente tarea recomendada: despues de mergear `m3-ingestion-pipeline`, empezar `m3-chunking-baseline`, porque ingestion ya produce `document_versions` y el proximo riesgo es crear chunks con offsets reproducibles antes de embeddings o retrieval.

## Politica para reducir conflictos de merge

- Solo un PR activo debe tocar migraciones Alembic y modelos SQLAlchemy a la vez.
- Abrir branches de repositories o workers solo despues de mergear el PR de schema.
- Mantener ediciones del roadmap en PRs de planificacion o cierre de milestone.
- No duplicar progreso rutinario en `docs/progress-log/`; OpenSpec archive, PRs y git son suficientes para cierres normales.
