# Tareas M22 de V1 product scope reset

## 1. Planificacion y setup

- [x] 1.1 Crear branch `codex/v1-product-scope-reset` desde el `origin/main`
  actual.
- [x] 1.2 Confirmar que M21/M21 fixes estan mergeados y no hay changes activos.
- [x] 1.3 Replantear v1 como producto terminado, no release de portafolio.

## 2. Change OpenSpec

- [x] 2.1 Crear propuesta, diseno y tasks de
  `m22-v1-product-scope-reset`.
- [x] 2.2 Agregar delta nuevo `v1-product-completion`.
- [x] 2.3 Agregar delta modificado para `v1-release-readiness`.

## 3. Docs de estado

- [x] 3.1 Actualizar `docs/progress.md` con M22 activo.
- [x] 3.2 Actualizar `docs/roadmap.md` con M21 como pre-v1 core readiness y
  M22 como reset activo.
- [x] 3.3 Actualizar `docs/architecture/v1-design.md` con la nueva decision.
- [x] 3.4 Actualizar `README.md` para no prometer tag/release v1.0.

## 4. Validacion

- [x] 4.1 Validar `openspec validate m22-v1-product-scope-reset --strict`.
- [x] 4.2 Validar `openspec validate --specs --strict`.
- [x] 4.3 Confirmar `openspec list`.
- [x] 4.4 Ejecutar `git diff --check`.
