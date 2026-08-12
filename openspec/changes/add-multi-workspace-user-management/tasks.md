## 1. Contrato y persistencia

- [x] 1.1 Agregar delta specs y retirar el plan fuera de OpenSpec.
- [x] 1.2 Escribir tests RED para email normalizado, credencial, sesion y
      compatibilidad de migracion.
- [x] 1.3 Implementar modelos, migracion Alembic y dependencia Argon2.

## 2. Autenticacion segura

- [x] 2.1 Escribir tests RED del servicio de password/sesion, expiracion y
      throttling.
- [x] 2.2 Implementar repositorios y servicio de autenticacion hash-only.
- [x] 2.3 Escribir tests RED de setup, login, me, csrf, cambio y logout.
- [x] 2.4 Implementar endpoints, cookie segura, Origin/CSRF, bearer fallback y
      eliminar bootstrap fail-open.

## 3. Usuarios y memberships

- [x] 3.1 Escribir tests RED de creacion atomica, reset, suspension/reactivacion
      y directorio global.
- [x] 3.2 Implementar API global superadmin y revocacion de sesiones.
- [x] 3.3 Escribir tests RED de listado/agregado por email/cambio/remocion por
      workspace y aislamiento entre workspaces.
- [x] 3.4 Implementar API de miembros y errores estables.
- [x] 3.5 Escribir tests PostgreSQL de concurrencia e implementar locks para el
      ultimo superadmin/admin activo.

## 4. Matriz de autorizacion

- [x] 4.1 Auditar todas las rutas por minimo rol y escribir tests
      discriminantes viewer/contributor/admin/superadmin.
- [x] 4.2 Corregir guards y demostrar que un rol en workspace A no concede
      permisos en workspace B.

## 5. Frontend

- [x] 5.1 Escribir tests RED del cliente cookie/CSRF, login y cambio obligatorio.
- [x] 5.2 Implementar frontera de sesion y retirar bearer humano de Vite.
- [x] 5.3 Escribir tests RED e implementar `OneTimePasswordDialog` con copia y
      limpieza irreversible.
- [x] 5.4 Escribir tests RED e implementar usuarios globales para superadmin.
- [x] 5.5 Escribir tests RED e implementar miembros del workspace para admin,
      navegacion y acciones por rol.

## 6. Calidad y entrega

- [x] 6.1 Actualizar configuracion de ejemplo, documentacion operativa y
      housekeeping; sincronizar specs canonicas y archivar el change.
- [x] 6.2 Ejecutar unit/integration/frontend, Ruff, mypy, build y migracion
      upgrade/downgrade/upgrade sobre PostgreSQL real.
- [x] 6.3 Ejecutar E2E local en navegador, buscar regresiones y corregirlas.
- [x] 6.4 Realizar revision de seguridad del diff y segunda pasada de errores
      (login throttle race, lockout por email, last-admin en rutas legacy,
      CSRF single-flight/retry, logout fail-closed).
- [x] 6.5 Commit intencional, push y PR a `main` con evidencia completa
      (`https://github.com/erevecov/adaptive-rag/pull/642`).
