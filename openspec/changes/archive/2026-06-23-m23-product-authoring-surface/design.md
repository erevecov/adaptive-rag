# Diseno M23 de product authoring surface

## Decision

M23 agrega la primera superficie publica de authoring para projects y sources.
El objetivo es que un usuario local pueda preparar datos propios sin tocar SQL
ni fixtures internas. La ingestion operativa queda fuera del slice para evitar
mezclar authoring, job lifecycle y worker UX en un PR demasiado grande.

## Superficie API

M23 debe definir endpoints publicos:

- `POST /projects`
- `GET /projects`
- `GET /projects/{project_id}`
- `POST /projects/{project_id}/sources`
- `GET /projects/{project_id}/sources`
- `GET /projects/{project_id}/sources/{source_id}`

Los responses deben ser JSON estable y no incluir secretos. Crear proyecto usa
`embedding_mode = dense` por defecto. En M23, la superficie publica no debe
promover `dense_sparse`; ese modo queda reservado hasta que otro OpenSpec
demuestre sparse retrieval de producto.

## Superficie CLI

M23 debe definir comandos:

- `adaptive-rag projects create`
- `adaptive-rag projects list`
- `adaptive-rag projects show`
- `adaptive-rag sources create`
- `adaptive-rag sources list`
- `adaptive-rag sources show`

La CLI emite JSON para que el runbook y scripts locales puedan componer el
flujo. Errores de proyecto inexistente, source inexistente, source duplicada o
contenido faltante deben ser estables y devolver exit code no cero.

## Source types

M23 soporta authoring para los source types ya entendidos por ingestion:

- `markdown`
- `text`
- `txt`
- `url`

Para `markdown`, `text` y `txt`, la superficie publica debe capturar contenido
en `extra_metadata.content`, porque el pipeline actual lee de ese campo. Para
`url`, `external_id` es la URL y M23 no debe hacer fetch ni SSRF checks en create;
la validacion de fetch sigue perteneciendo a ingestion.

## Frontend

El frontend debe agregar controles compactos para crear o seleccionar proyecto y
agregar/listar sources. Esto debe integrarse en la experiencia de trabajo
actual, no en una landing page. Chat, history y observability siguen siendo
superficies existentes; M23 solo les da un camino mas realista para obtener
`project_id` y sources.

## Fuera de alcance

- Encolar jobs `ingest_source`.
- Mostrar job status, failure reason, retry o dead-letter.
- Ejecutar worker desde API o browser.
- Crear document versions, chunks o embeddings durante authoring.
- Agregar auth multi-user, PDF/Office, voice, MCP o graph default.

## Secuencia recomendada

1. `m23-product-authoring-surface`: planning/OpenSpec.
2. `m23-authoring-api-contract`: repositories, schemas y endpoints.
3. `m23-authoring-cli`: comandos JSON de projects/sources.
4. `m23-authoring-frontend`: cliente y UI compacta para projects/sources.
5. `m23-quality-gate`: validacion, docs y archive.

## Riesgos

- Si M23 intenta encolar ingestion, se mezcla con M24. Mantener authoring como
  persistencia de identidad/source metadata.
- Si la UI se vuelve un wizard grande, desplaza el foco de producto. Mantener
  controles compactos y operativos.
- Si se expone `dense_sparse` como modo normal, se contradice M22. Mantenerlo
  reservado hasta evidencia nueva.
