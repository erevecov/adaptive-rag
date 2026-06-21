# Diseno M15 de frontend inicial de chat

## Contexto

M5 cerro el contrato conversacional minimo con `POST /projects/{project_id}/chat`.
M13 persistio audit trail durable y M14 expuso lectura read-only con:

- `GET /projects/{project_id}/chat/sessions`
- `GET /projects/{project_id}/chat/sessions/{session_id}`

El repo no contiene frontend todavia. La documentacion actual de Vite,
consultada via `ctx7`, confirma que el scaffold oficial sigue siendo
`create-vite` y que el template React TypeScript usa `@vitejs/plugin-react`.
La implementacion debe fijar versiones en su lockfile cuando llegue el slice de
scaffold, no en este PR de planificacion.

## Decision

La decision recomendada es `proceed` con M15 como frontend inicial de chat e
historial, empezando por un scaffold React/TypeScript con Vite en un directorio
dedicado, probablemente `frontend/`.

Vite es suficiente para la primera superficie porque el producto necesita una
app cliente operativa contra API existente, no SSR, routing complejo ni backend
frontend. React mantiene el stack familiar para componentes, estado local,
formularios y testing de UI. El primer objetivo es experiencia usable, no
marketing ni dashboard.

## Objetivos

- Crear un frontend dedicado y aislado del paquete Python.
- Configurar base URL de API desde variable publica de build/dev, sin secretos.
- Enviar preguntas con `POST /projects/{project_id}/chat`.
- Mostrar answer, citations, tool calls minimas y `session_id` cuando exista.
- Listar sesiones persistidas por proyecto usando M14.
- Consultar detalle de una sesion sin re-ejecutar chat ni retrieval.
- Refrescar historial despues de una pregunta exitosa.
- Mantener UI densa, operativa y orientada a debugging/productividad.
- Dejar build, lint, tests y dev server documentados para QA local.

## No objetivos

- No implementar streaming SSE ni WebSockets.
- No implementar dashboards de costo/latencia.
- No implementar replay/re-run de sesiones.
- No editar, borrar, archivar ni retener sesiones desde UI.
- No cambiar API backend, CLI, ranking, retrieval, rerank, providers ni
  defaults.
- No agregar autenticacion/autorizacion final.
- No almacenar provider keys ni secretos en el browser.
- No crear landing page ni contenido de marketing.

## Contrato frontend recomendado

### Stack y estructura

- Directorio dedicado: `frontend/`.
- React + TypeScript + Vite.
- Scripts esperados:
  - `dev`
  - `build`
  - `lint`
  - `test`
- Configuracion de API:
  - `VITE_ADAPTIVE_RAG_API_BASE_URL` o nombre equivalente documentado.
  - default local apuntando al backend FastAPI solo en archivo de ejemplo.
  - ningun secreto requerido en variables `VITE_*`.

### Cliente API

El cliente debe envolver `fetch` con:

- base URL configurada;
- serializacion JSON estable;
- errores legibles para HTTP no exitoso;
- tipos TypeScript alineados con los schemas backend actuales;
- funciones separadas para:
  - `askChat(projectId, body)`;
  - `listChatSessions(projectId, params)`;
  - `getChatSession(projectId, sessionId)`.

### Experiencia UI

La primera pantalla debe ser la app operativa:

- selector/input de `project_id`;
- panel de sesiones recientes;
- panel principal de conversacion/pregunta;
- detalle read-only de la sesion seleccionada;
- citations visibles junto a la respuesta;
- estados de loading, error y empty state;
- controls acotados para `retrieval_limit` y metadata filter solo si el contrato
  se mantiene simple en el slice de implementacion.

## Secuencia recomendada de M15

### 1. `m15-chat-frontend-plan`

Alcance:

- Crear el change OpenSpec M15.
- Documentar objetivos, no objetivos, stack recomendado y slices.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo frontend.
- Dependencias Node/lockfile.

### 2. `m15-frontend-scaffold`

Alcance:

- Crear `frontend/` con React/TypeScript/Vite.
- Agregar scripts `dev`, `build`, `lint` y `test`.
- Agregar configuracion minima de tooling y README local.
- Validar que el build inicial corre sin depender del backend.

Fuera de alcance:

- Integracion real con API.

### 3. `m15-chat-api-client`

Alcance:

- Agregar tipos y cliente fetch para `POST /chat` y `chat-history`.
- Manejar errores HTTP y estados de red de forma testeable.
- Agregar fixtures o mocks para tests sin backend live.

Fuera de alcance:

- Componentes visuales completos.

### 4. `m15-chat-workspace-ui`

Alcance:

- Construir la vista principal de pregunta/respuesta.
- Mostrar answer, citations y tool calls minimas.
- Refrescar historial despues de una respuesta exitosa.

Fuera de alcance:

- Streaming o respuesta parcial.

### 5. `m15-chat-history-ui`

Alcance:

- Listar sesiones por proyecto.
- Mostrar detalle read-only de sesion.
- Cubrir loading, empty, error y seleccion de sesion.

Fuera de alcance:

- Replay, delete, edit o dashboard.

### 6. `m15-quality-gate`

Alcance:

- Validar build/lint/test frontend.
- Validar tests Python existentes cuando cambie contrato compartido.
- Validar OpenSpec.
- Documentar comando local para probar API + frontend.
- Archivar el change M15 cuando la implementacion quede completa.

## Riesgos y mitigaciones

- Riesgo: el primer frontend se convierta en dashboard.
  Mitigacion: M15 solo cubre chat e historial read-only.
- Riesgo: exponer secretos en el browser.
  Mitigacion: solo variables publicas `VITE_*` sin API keys ni provider
  credentials.
- Riesgo: UI dependa de shapes backend no versionados.
  Mitigacion: tipos frontend reflejan schemas HTTP actuales y tests usan
  fixtures.
- Riesgo: setup Node contamine el paquete Python.
  Mitigacion: directorio `frontend/` aislado y comandos documentados.
- Riesgo: mezclar streaming con submit basico.
  Mitigacion: `POST /chat` request/response sigue siendo el unico flujo de ask
  en M15.

## Validacion esperada por slice

Planificacion:

```text
npx --yes @fission-ai/openspec validate m15-chat-frontend-plan --strict
npx --yes @fission-ai/openspec validate --specs --strict
npx --yes @fission-ai/openspec list
git diff --check
```

Implementacion posterior:

```text
uv run pytest
uv run ruff check .
uv run mypy src
cd frontend && <package-manager> run lint
cd frontend && <package-manager> run test
cd frontend && <package-manager> run build
```
