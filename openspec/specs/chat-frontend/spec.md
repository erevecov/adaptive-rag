# chat-frontend Specification

## Purpose
Define la primera superficie frontend de Adaptive RAG para chat e historial
read-only sobre los contratos backend existentes, manteniendo el cliente
aislado bajo `frontend/` y sin ampliar el alcance de retrieval, providers,
streaming, replay o dashboards.

## Requirements
### Requirement: Frontend inicial usa scaffold dedicado

El sistema MUST agregar un frontend dedicado para la primera UI de chat sin
mezclar dependencias Node con el paquete Python principal.

#### Scenario: Scaffold queda aislado

- **WHEN** se implemente el scaffold frontend de M15
- **THEN** los archivos de app, build tooling y lockfile Node quedan bajo un
  directorio dedicado como `frontend/`
- **AND** el paquete Python existente sigue instalable y testeable sin instalar
  dependencias Node

#### Scenario: Stack usa React TypeScript con Vite

- **WHEN** se cree el frontend inicial
- **THEN** usa React, TypeScript y Vite con plugin React oficial o equivalente
  vigente al momento de implementacion
- **AND** expone scripts documentados para dev, build, lint y test

### Requirement: Frontend consume contratos API existentes

El sistema MUST consumir los contratos HTTP ya cerrados para chat e historial,
sin consultar tablas internas ni duplicar logica backend.

#### Scenario: Cliente envia pregunta de chat

- **WHEN** el usuario envia una pregunta desde la UI con `project_id`
- **THEN** el frontend llama `POST /projects/{project_id}/chat`
- **AND** muestra `answer`, `citations`, `tool_calls` y `session_id` cuando
  existan en la respuesta

#### Scenario: Cliente lista sesiones persistidas

- **WHEN** el usuario abre o refresca el historial de un proyecto
- **THEN** el frontend llama `GET /projects/{project_id}/chat/sessions`
- **AND** renderiza sesiones ordenadas segun el contrato backend
- **AND** soporta limite/cursor solo mediante parametros publicos del endpoint

#### Scenario: Cliente muestra detalle read-only

- **WHEN** el usuario selecciona una sesion persistida
- **THEN** el frontend llama
  `GET /projects/{project_id}/chat/sessions/{session_id}`
- **AND** muestra mensajes, tool calls, retrieval runs, citations y provider
  usage disponibles
- **AND** no re-ejecuta chat, retrieval ni providers

### Requirement: UI base es operativa y no marketing

El sistema MUST presentar una experiencia de trabajo directa para chat e
historial como primera pantalla del frontend.

#### Scenario: Primera pantalla permite trabajar

- **WHEN** el usuario abre la app frontend
- **THEN** ve controles para elegir o ingresar `project_id`, enviar una pregunta
  y revisar sesiones recientes
- **AND** no se muestra una landing page como pantalla principal

#### Scenario: Estados basicos quedan cubiertos

- **WHEN** la UI espera una respuesta, no tiene datos o recibe error HTTP/red
- **THEN** muestra estados de loading, empty y error claros
- **AND** preserva el input del usuario cuando una solicitud falla

### Requirement: Frontend no expone secretos ni cambia alcance backend

El sistema MUST mantener el frontend como cliente de API sin secretos y sin
alterar contratos backend fuera del alcance M15.

#### Scenario: Configuracion publica no contiene credenciales

- **WHEN** se configure la base URL del backend para dev/build
- **THEN** se usa una variable publica de frontend como
  `VITE_ADAPTIVE_RAG_API_BASE_URL` o equivalente
- **AND** no se requiere ni documenta provider API key en el browser

#### Scenario: M15 no agrega streaming ni replay

- **WHEN** M15 quede implementado
- **THEN** no agrega endpoints SSE/WebSocket
- **AND** no agrega replay, delete, edit, retention ni dashboards
- **AND** no cambia retrieval, rerank, providers ni defaults de ranking
