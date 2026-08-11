# Change: Gestion humana multi-workspace

## Why

Adaptive RAG ya separa identidades globales de memberships por workspace, pero
el navegador depende de bearer tokens y la administracion combina identidades y
memberships en una superficie incompleta. Se necesita autenticacion humana y un
flujo seguro para que un mismo usuario tenga roles distintos por workspace.

## What Changes

- Renombrar el identificador humano `login` a `email`, unico y normalizado.
- Agregar credenciales Argon2id, sesiones opacas hash-only, CSRF y bootstrap
  protegido por secreto de instalacion.
- Mantener bearer tokens solo como credenciales tecnicas para CLI/MCP/scripts.
- Agregar gestion global de usuarios para `superadmin` y gestion de miembros
  por workspace para `admin`.
- Generar passwords temporales que se muestran una sola vez y obligan cambio en
  el primer login.
- Proteger el ultimo superadmin activo y el ultimo admin activo de cada
  workspace, incluyendo mutaciones concurrentes.
- Separar en frontend login, cambio obligatorio de password, usuarios globales
  y miembros del workspace con navegacion por rol.
- Conservar memberships al suspender usuarios y revocar todas sus sesiones.

## Impact

- **Specs:** `project-rbac`, `chat-frontend`, `product-authoring-surface`.
- **Backend:** modelos/migracion, repositorios, servicio de autenticacion,
  dependencias y rutas HTTP.
- **Frontend:** cliente de API, frontera de sesion y superficies administrativas.
- **Compatibilidad:** los bearer tokens existentes siguen funcionando; se
  elimina el bootstrap implicito por tabla vacia.

## Out of Scope

- Invitaciones o recuperacion por email.
- SSO/OIDC/MFA.
- Borrado fisico de usuarios.
- Roles personalizados y UI de API keys.
