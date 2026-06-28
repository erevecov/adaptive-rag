# Proposal M37 project RBAC chat knowledge

## Why

Adaptive RAG ya trata `projects` como frontera de aislamiento RAG, pero el
producto sigue siendo local-single-user: no hay `users`, membresias por
proyecto, ownership de sesiones ni permisos para separar quien puede chatear,
administrar miembros o gestionar conocimiento.

El siguiente salto de producto es convertir los proyectos en espacios
compartidos donde:

- todas las sesiones de chat viven dentro de un proyecto;
- cada usuario ve solo sus propias sesiones;
- todos los usuarios pueden descubrir nombres de proyectos;
- solo usuarios asignados pueden entrar a un proyecto;
- `superadmin` administra todo el sistema;
- `admin`, `contributor` y `viewer` operan por proyecto;
- el conocimiento del proyecto se comparte, pero las propuestas desde chat
  pasan por aprobacion cuando vienen de `viewer`.

Este cambio toma como referencia el flujo de BeFlow para chat-learned facts:
una propuesta de conocimiento conserva origen de chat, entra como `pending`
cuando requiere revision y se transforma en conocimiento indexable solo al
aprobarse.

## What Changes

- Agregar el change OpenSpec `m37-project-rbac-chat-knowledge`.
- Definir auth local first-party para M37:
  - `users` locales;
  - tokens/sesiones locales para resolver `current_user`;
  - `superadmin` como rol de sistema.
- Definir membresias por proyecto con roles `admin`, `contributor` y `viewer`.
- Definir que el listado de proyectos muestra nombres de todos los proyectos,
  pero expone acceso efectivo por usuario.
- Definir ownership de `chat_sessions` por `user_id`.
- Definir autorizacion para las rutas existentes de authoring, ingestion,
  retrieval, chat, history, observability, runtime settings y admin.
- Definir `knowledge_proposals` para conocimiento propuesto desde chat.
- Definir aprobacion directa para `contributor+` y cola `pending` para
  propuestas de `viewer`.
- Definir endpoints y UI para gestion de usuarios, miembros de proyecto y
  revision de conocimiento.
- Planear implementacion en slices secuenciales para no mezclar schema,
  autorizacion, chat, ingestion y UI en un solo paso opaco.

## Out of Scope

- No integrar Supabase, Clerk, Auth0 ni otro JWT externo en M37.
- No implementar SSO, email verification, password reset ni multi-tenant
  hosted deployment.
- No permitir que un `admin` de proyecto archive o elimine proyectos.
- No permitir que usuarios lean sesiones de chat privadas de otros usuarios.
- No exponer provider secrets ni settings globales a roles de proyecto.
- No cambiar el ranking/retrieval default.
- No crear conocimiento indexable desde una propuesta `pending`.

## Validation

- Validar este OpenSpec change con `npx --yes @fission-ai/openspec validate
  m37-project-rbac-chat-knowledge --strict`.
- Validar specs canonicas con `npx --yes @fission-ai/openspec validate --specs
  --strict --no-interactive`.
- La implementacion futura debe usar TDD por slice:
  - schema/repositories;
  - auth dependencies;
  - project/member APIs;
  - chat session privacy;
  - knowledge proposal workflow;
  - frontend selector/admin/review queue.
- El smoke final debe probar:
  1. superadmin crea proyecto y usuario;
  2. asigna viewer a proyecto;
  3. viewer chatea y propone conocimiento;
  4. contributor aprueba/refina;
  5. ingestion indexa;
  6. chat posterior cita el conocimiento aprobado;
  7. otro usuario no puede ver sesiones privadas del viewer.
