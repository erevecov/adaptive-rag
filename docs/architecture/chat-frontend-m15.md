# M15 Chat frontend inicial

## Decision

M15 abre la primera superficie frontend de Adaptive RAG sobre contratos backend
ya cerrados: `POST /chat` de M5 y `chat-history` de M14.

La razon es que M14 dejo una API read-only estable para historial, pero el repo
todavia no tiene frontend. Antes de streaming, dashboards o replay, conviene
construir una app operativa pequena que permita enviar preguntas, revisar
citations y navegar sesiones persistidas sin tocar queries internas.

## Alcance recomendado

- Crear un scaffold frontend dedicado, recomendado como `frontend/`.
- Usar React + TypeScript + Vite para una app cliente liviana.
- Configurar base URL de API con variable publica de frontend, sin secretos.
- Agregar cliente API tipado para `POST /chat`, listado de sesiones y detalle.
- Construir una pantalla operativa con input de `project_id`, pregunta,
  respuesta, citations y panel de historial.
- Cubrir loading, empty, error y refresh de historial despues de una pregunta.

## Fuera de alcance

- Streaming SSE y WebSockets.
- Dashboard de costo/latencia.
- Replay/re-run, edit, delete o retention de sesiones.
- Auth/autorizacion final.
- Cambios de API backend, CLI, retrieval, rerank, providers o defaults.
- Landing page o marketing como primera pantalla.

## Secuencia

1. `m15-chat-frontend-plan`: activo.
2. `m15-frontend-scaffold`: crear app React/TypeScript/Vite aislada.
3. `m15-chat-api-client`: agregar tipos y cliente fetch testeable.
4. `m15-chat-workspace-ui`: construir pregunta/respuesta con citations.
5. `m15-chat-history-ui`: construir listado/detalle read-only.
6. `m15-quality-gate`: validar y archivar el change.

## Criterio de cierre

M15 debe cerrar cuando un usuario pueda abrir el frontend local, configurar un
`project_id`, enviar una pregunta por el endpoint existente, ver respuesta con
citations y revisar sesiones persistidas desde la API M14, sin streaming ni
mutaciones de historial.
