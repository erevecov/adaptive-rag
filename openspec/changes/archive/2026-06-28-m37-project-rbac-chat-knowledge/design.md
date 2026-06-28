# Design M37 project RBAC chat knowledge

## Context

El schema actual aísla datos por `project_id`, pero no por usuario. Las rutas
publicas operan sin actor y `chat_sessions` solo tiene `project_id`, por lo que
el historial de chat de un proyecto es compartido por defecto.

M37 cambia esa frontera:

- proyecto: espacio compartido de conocimiento, runtime overrides,
  ingestion/retrieval y herramientas;
- usuario: dueño privado de sus sesiones dentro de cada proyecto;
- membresia: permiso efectivo de un usuario dentro de un proyecto;
- propuesta de conocimiento: puente auditable entre chat privado y
  conocimiento compartido del proyecto.

La decision aprobada para M37 es auth local first-party. El diseño debe dejar
un adapter claro para JWT externo posterior, pero no depender de proveedor
externo para cerrar RBAC.

## Domain Model

### Users

`users` representa identidad local:

- `id`
- `email` o `username` unico;
- `display_name`;
- `system_role`: `superadmin` o `user`;
- `is_active`;
- timestamps.

`superadmin` es rol global. No se modela como membresia en cada proyecto.

Para resolver `current_user`, M37 puede usar tokens locales persistidos:

- `user_access_tokens.user_id`;
- hash de token, no plaintext;
- label, timestamps, optional expiration y revoked marker.

El frontend local puede guardar un bearer token ingresado o emitido por flujo
local. La validacion de token vive en un dependency adapter para que una futura
integracion JWT reemplace solo esa pieza.

### Project memberships

`project_memberships` enlaza `project_id`, `user_id` y rol:

- `admin`
- `contributor`
- `viewer`

Reglas:

- Un usuario tiene como maximo una membresia activa por proyecto.
- `superadmin` puede crear, modificar o remover cualquier membresia.
- `admin` puede gestionar membresias solo de su proyecto.
- `admin` no puede crear `superadmin` ni modificar roles globales.
- El rol maximo que un `admin` puede asignar en su proyecto es `admin`.
- `contributor` y `viewer` no gestionan membresias.

### Project discovery and access

El listado de proyectos queda dividido conceptualmente en:

- discovery: todos los usuarios autenticados pueden ver `id`, `name` y estado
  publico no sensible de todos los proyectos;
- access: solo `superadmin` o usuarios con membresia pueden abrir un proyecto.

La respuesta de listado debe incluir algo equivalente a:

- `access_status`: `accessible` o `locked`;
- `role`: `superadmin`, `admin`, `contributor`, `viewer` o `none`.

Rutas project-scoped deben verificar acceso real, no confiar en que el frontend
oculte proyectos locked.

### Chat ownership

`chat_sessions` gana `user_id`.

Reglas:

- crear chat requiere `viewer+` en el proyecto;
- la sesion creada pertenece al `current_user`;
- listar sesiones devuelve solo sesiones del `current_user`;
- consultar detalle devuelve 404 cuando la sesion pertenece a otro usuario,
  incluso dentro del mismo proyecto;
- `superadmin` no lee sesiones privadas por defecto. Cualquier auditoria
  cross-user futura debe ser capability explicita y separada.

Mensajes, tool calls, retrieval runs y provider usage siguen colgados de la
sesion y el proyecto. La privacidad se aplica entrando por la sesion owner.

### Knowledge proposals

`knowledge_proposals` representa conocimiento candidato antes de volverse
source/document indexable.

Campos principales:

- `id`
- `project_id`
- `status`: `pending`, `approved`, `rejected`
- `proposed_text`
- `refined_text`
- `submitted_by_user_id`
- `reviewed_by_user_id`
- `origin_session_id`
- `origin_message_id`
- `source_id` creado al aprobar
- `rejection_reason`
- timestamps.

La propuesta conserva el origen de chat para review. El texto indexable es
`refined_text` si existe, si no `proposed_text`.

## Permission Matrix

`superadmin`:

- ve, crea y administra todos los usuarios;
- ve, crea y administra todos los proyectos;
- asigna cualquier rol de proyecto;
- puede gestionar conocimiento de cualquier proyecto;
- puede configurar runtime settings globales.

`admin` por proyecto:

- accede a chat, retrieval, authoring, ingestion, observability y runtime
  overrides del proyecto;
- gestiona miembros solo de su proyecto;
- puede asignar `viewer`, `contributor` o `admin`;
- gestiona conocimiento del proyecto;
- no archiva ni elimina proyectos;
- no gestiona usuarios globales ni provider secrets globales.

`contributor` por proyecto:

- usa chat;
- crea conocimiento aprobado directo;
- ve propuestas pendientes de cualquier usuario del proyecto;
- aprueba, rechaza o refina propuestas pendientes.

`viewer` por proyecto:

- usa chat;
- propone conocimiento desde chat;
- sus propuestas quedan `pending` hasta revision.

## API Shape

Auth/system:

- `GET /me`
- `GET /users`
- `POST /users`
- `PATCH /users/{user_id}`
- `POST /users/{user_id}/tokens`
- `DELETE /users/{user_id}/tokens/{token_id}`

Projects:

- `GET /projects` devuelve discovery con acceso efectivo.
- `POST /projects` requiere `superadmin`.
- `GET /projects/{project_id}` requiere acceso o `superadmin`.
- project archive/delete, si existen en M37 o despues, requieren
  `superadmin`.

Project members:

- `GET /projects/{project_id}/members` requiere `admin+`.
- `PUT /projects/{project_id}/members/{user_id}` requiere `admin+`.
- `DELETE /projects/{project_id}/members/{user_id}` requiere `admin+`.

Knowledge proposals:

- `POST /projects/{project_id}/knowledge/proposals` requiere `viewer+`.
- `GET /projects/{project_id}/knowledge/proposals?status=pending` requiere
  `contributor+`.
- `GET /projects/{project_id}/knowledge/proposals/{proposal_id}` requiere
  `contributor+` para pending queue, o submitter para su propia propuesta.
- `POST /projects/{project_id}/knowledge/proposals/{proposal_id}/approve`
  requiere `contributor+`.
- `POST /projects/{project_id}/knowledge/proposals/{proposal_id}/reject`
  requiere `contributor+`.
- `POST /projects/{project_id}/knowledge/proposals/{proposal_id}/refine`
  requiere `contributor+`.

Existing routes get guards:

- chat/retrieval/source read: `viewer+`;
- source create and ingestion jobs: `contributor+`;
- chat observability and project runtime overrides: `admin+`;
- global runtime settings/provider secrets: `superadmin`.

## Knowledge Flow

1. User chats in a project.
2. User explicitly proposes knowledge from the chat UI, or a future detector
   creates a candidate with user confirmation.
3. Backend writes `knowledge_proposals` with chat origin.
4. If actor is `viewer`, proposal stays `pending`.
5. If actor is `contributor+`, proposal is approved in the same transaction
   or same service operation.
6. Approval creates a project source using existing text source contract:
   `source_type = "text"` or a dedicated `chat` source type if introduced by
   implementation and spec.
7. Approval enqueues an explicit `ingest_source` job.
8. Ingestion/chunking/embedding pipelines convert approved knowledge into
   retrievable chunks.

Pending proposals are not visible to retrieval and do not create chunks.

## Frontend

The current manual project id input becomes a searchable project selector:

- all project names are visible;
- locked projects are visible but disabled;
- selecting a locked project does not fire chat/authoring requests;
- selected accessible project drives chat, history, retrieval, authoring,
  ingestion and runtime override calls.

Admin surfaces:

- `superadmin` sees global users and project creation.
- `admin+` sees project members.
- `contributor+` sees knowledge review queue.
- viewer sees chat and proposal status for their own submitted proposals.

The UI should keep M36 workspace anatomy: session rail, chat center, right
inspector. Project switching resets selected session because session ownership
is user/project scoped.

## Error Handling

Stable authorization errors:

- `authentication_required`
- `inactive_user`
- `project_access_denied`
- `project_role_required`
- `system_role_required`
- `cannot_assign_system_role`
- `cannot_assign_project_role`
- `cannot_manage_project_members`
- `cannot_view_private_session`
- `knowledge_proposal_not_pending`

For privacy, cross-user chat session access should return 404 or an equivalent
not-found detail, not a response that reveals another user's session exists.

## Sequencing

1. `m37-project-rbac-chat-knowledge`: OpenSpec planning and validation.
2. `m37-auth-schema-repositories`: users, tokens, memberships, ownership and
   proposal models/repositories.
3. `m37-auth-dependencies-api-guards`: current user resolver and backend guards
   on public routes.
4. `m37-private-chat-sessions`: chat create/list/detail under current user.
5. `m37-project-admin-users`: user and project membership APIs.
6. `m37-knowledge-proposals`: proposal queue, approve/reject/refine and
   ingestion bridge.
7. `m37-frontend-project-rbac`: selector, locked projects, admin/member UI and
   knowledge review queue.
8. `m37-quality-gate`: full backend/frontend/OpenSpec/browser QA and archive.

## Risks

- **Auth scope creep.** Full hosted auth could delay RBAC. Mitigation: local
  first-party token adapter now, external JWT adapter later.
- **Privacy regression.** Existing chat history is project-only. Mitigation:
  change repositories and route tests to require `user_id`.
- **Knowledge pipeline duplication.** Proposals could bypass existing sources.
  Mitigation: approval feeds existing source/ingestion pipeline.
- **Role ambiguity.** `admin` is project-scoped, not global. Mitigation:
  separate `users.system_role` from `project_memberships.role`.
- **Parallel migration conflicts.** M37 touches Alembic/models. Mitigation:
  one schema PR first, then dependent slices.
