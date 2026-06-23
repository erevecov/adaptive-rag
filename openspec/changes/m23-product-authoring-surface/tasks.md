# Tareas M23 de product authoring surface

## 1. Planificacion y setup

- [x] 1.1 Confirmar que PR #115 esta mergeado en `origin/main`.
- [x] 1.2 Crear branch `codex/m23-product-authoring-surface` desde el
  `origin/main` actual.
- [x] 1.3 Confirmar que `openspec list` no muestra changes activos despues de
  M22.
- [x] 1.4 Revisar repositories, modelos, rutas API, CLI y frontend client
  existentes para projects/sources.

## 2. Change OpenSpec

- [x] 2.1 Agregar propuesta, diseno y tasks de
  `m23-product-authoring-surface`.
- [x] 2.2 Agregar capability nueva `product-authoring-surface`.
- [x] 2.3 Agregar deltas para `v1-product-completion`, `domain-schema`,
  `repositories` y `chat-frontend`.

## 3. Docs de estado

- [x] 3.1 Actualizar `docs/progress.md` con M23 activo.
- [x] 3.2 Actualizar `docs/roadmap.md` con M23 activo y la secuencia propuesta.
- [x] 3.3 Actualizar `docs/architecture/v1-design.md` con el alcance M23.
- [x] 3.4 Agregar plan de implementacion en `docs/superpowers/plans/`.

## 4. Validacion

- [x] 4.1 Validar `openspec validate m23-product-authoring-surface --strict`.
- [x] 4.2 Validar `openspec validate --specs --strict`.
- [x] 4.3 Confirmar `openspec list`.
- [x] 4.4 Ejecutar `git diff --check`.
