# Design: Gestion humana multi-workspace

## Invariantes

1. `User` es una identidad global con `system_role = user | superadmin`.
2. `WorkspaceMembership` es la unica fuente de `viewer | contributor | admin`.
3. Un usuario puede tener un rol independiente en cada workspace.
4. Los roles son acumulativos: `admin > contributor > viewer`.
5. `superadmin` tiene autoridad global sin necesitar memberships.
6. Un admin solo ve y muta miembros de sus propios workspaces.
7. Nunca puede quedar el sistema sin un superadmin activo ni un workspace con
   miembros activos sin un admin activo.

## Modelo de datos

`users.login` se renombra a `users.email`, se normaliza con trim + lowercase y
mantiene unicidad. La migracion conserva IDs, tokens, memberships e historiales.

`user_password_credentials` es uno-a-uno con `users` y contiene
`password_hash`, `must_change_password`, `password_changed_at` y timestamps.
La aplicacion usa Argon2id con memoria 19 MiB, dos iteraciones y paralelismo uno.
Los passwords aceptan 15-128 caracteres Unicode; no exigen composicion ni
rotacion periodica.

`user_sessions` guarda un hash SHA-256 del token opaco y otro del token CSRF,
ademas de `last_seen_at`, expiracion absoluta, revocacion y timestamps. El token
de sesion se genera con 32 bytes aleatorios. Tiene 12 horas de expiracion idle y
7 dias de expiracion absoluta.

`login_attempts` registra hashes del email y de la IP, resultado y timestamp.
El throttle cuenta 10 fallos por par (email, IP) y 30 fallos por IP en 15
minutos; no hay hard-lock por email solo, para evitar DoS de cuentas desde
redes ajenas. En PostgreSQL el count+insert se serializa con advisory locks.
La respuesta de login es indistinguible para email inexistente, password
incorrecto, usuario suspendido y credencial ausente.

`user_access_tokens` se conserva sin cambios como credencial tecnica hash-only.

## Autenticacion

### Bootstrap

`POST /auth/setup` solo funciona cuando no existe ningun usuario y requiere
`X-Setup-Secret`, comparado en tiempo constante contra
`ADAPTIVE_RAG_BOOTSTRAP_SECRET`. Crea atomicamente el primer superadmin y su
password. El secreto no se persiste ni se devuelve. Desaparece el principal
bootstrap concedido automaticamente por una tabla vacia.

### Sesion humana

`POST /auth/login` verifica email/password, aplica throttling, rehash oportunista
y crea una sesion. La cookie `adaptive_rag_session` es `HttpOnly`, `SameSite=Lax`,
`Path=/` y `Secure` fuera de local/test. El frontend usa `credentials: include`.

`GET /auth/me` acepta primero la cookie y, si no existe, bearer tecnico.
`GET /auth/csrf` devuelve el token CSRF solo para una sesion valida. Toda
mutacion autenticada por cookie valida `Origin` contra la allowlist y
`X-CSRF-Token` en tiempo constante. Bearer tecnico no requiere CSRF.

`POST /auth/change-password` valida el password actual salvo que la credencial
este marcada para cambio obligatorio, actualiza el hash, limpia el flag y revoca
las demas sesiones. `POST /auth/logout` revoca la sesion actual y borra cookie.

## Administracion global

Solo `superadmin` accede a `/admin/users`:

- lista/busca identidades y sus memberships;
- crea un superadmin sin membership o un usuario ordinario con membership
  inicial obligatorio;
- actualiza email, nombre y rol global;
- suspende/reactiva, preservando memberships y revocando sesiones al suspender;
- resetea password y recibe una password temporal exactamente una vez.

Creacion y reset usan `secrets.token_urlsafe(32)`. La respuesta que contiene la
password lleva `Cache-Control: no-store`; ni logs ni lecturas posteriores pueden
recuperarla.

## Administracion de workspace

`GET /workspaces/{workspace_id}/members` lista identidad, estado y rol solo de
ese workspace. `POST` agrega por email exacto una identidad existente y `PATCH`
actualiza el rol. `DELETE` elimina el membership. Admin puede asignar cualquiera
de los tres roles, pero no crear identidades ni cambiar atributos globales.

La proteccion de ultimo admin considera solo usuarios activos. Las mutaciones que
pueden retirar autoridad bloquean las filas relevantes con `SELECT ... FOR
UPDATE` dentro de una unica transaccion y vuelven a contar antes de escribir.
La misma disciplina protege el ultimo superadmin.

## Permisos

- `viewer`: chat, retrieval/RAG y su propio historial.
- `contributor`: viewer mas fuentes, ingestion y conocimiento compartido.
- `admin`: contributor mas configuracion y miembros del workspace.
- `superadmin`: todo lo anterior en todos los workspaces y administracion global.

Ningun rol de un workspace autoriza otro. Un usuario suspendido no puede iniciar
sesion ni usar sesiones/bearers, pero sus memberships se conservan.

## Frontend

La aplicacion arranca consultando `/auth/me`; 401 muestra login y
`must_change_password` muestra una pantalla bloqueante. Ya no lee bearer tokens
de Vite para autenticacion humana.

`Usuarios globales` aparece solo para superadmin y permite crear, editar,
suspender/reactivar y resetear passwords. `Miembros` aparece a admin en el
workspace activo y agrega usuarios existentes por email. Contributor ve las
superficies de conocimiento; viewer ve solo RAG/chat.

`OneTimePasswordDialog` muestra email y password temporal una sola vez, ofrece
copiar al portapapeles, feedback accesible y advertencia de cierre irreversible.
El estado se limpia al cerrar y no se persiste.

## Errores estables

Los errores de dominio se representan como `detail.code`: `invalid_credentials`,
`authentication_required`, `inactive_user`, `password_change_required`,
`csrf_failed`, `rate_limited`, `email_already_exists`, `user_not_found`,
`membership_not_found`, `workspace_access_required`,
`workspace_admin_required`, `superadmin_required`,
`last_active_superadmin` y `last_active_workspace_admin`.

## Seguridad y auditoria

Passwords, cookies, CSRF y secretos nunca se registran. Las respuestas sensibles
usan `no-store`. Los cambios administrativos generan logs estructurados con
actor, objetivo, workspace cuando aplica, accion y resultado, sin secretos.
Las cookies son host-only; CORS mantiene origenes explicitos y credenciales.

## Verificacion

Se usan tests unitarios para normalizacion, hashing, expiracion y rol; tests de
repositorio/migracion en PostgreSQL; tests de API para sesiones, CSRF, throttling,
matriz multi-workspace e invariantes; tests de componentes/cliente; y un E2E real
en navegador con dos workspaces, roles distintos, suspension y reset.
