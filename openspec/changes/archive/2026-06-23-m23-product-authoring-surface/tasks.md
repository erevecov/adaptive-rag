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

## 5. Implementacion API/repositories

- [x] 5.1 Agregar tests rojos para `ProjectRepository.list()` y endpoints de
  authoring.
- [x] 5.2 Implementar `ProjectRepository.list()` sin commits implicitos.
- [x] 5.3 Agregar schemas y routes HTTP para crear/listar/ver projects.
- [x] 5.4 Agregar schemas y routes HTTP para crear/listar/ver sources
  project-scoped.
- [x] 5.5 Validar que crear source no encola jobs ni ejecuta ingestion.
- [x] 5.6 Confirmar tests de repository/API.

## 6. Implementacion CLI

- [x] 6.1 Agregar tests rojos para `adaptive-rag projects create|list|show`.
- [x] 6.2 Agregar tests rojos para `adaptive-rag sources create|list|show`.
- [x] 6.3 Implementar comandos CLI de projects y sources con JSON por stdout.
- [x] 6.4 Confirmar errores estables por stderr para project/source faltante,
  source duplicado y content faltante.
- [x] 6.5 Confirmar que crear sources por CLI no encola ingestion jobs.

## 7. Implementacion frontend

- [x] 7.1 Agregar tests rojos de `apiClient` para projects/sources.
- [x] 7.2 Implementar tipos y metodos frontend de projects/sources.
- [x] 7.3 Agregar vista compacta de authoring integrada con chat/history/
  observability.
- [x] 7.4 Confirmar que seleccionar/crear project actualiza el `projectId`
  compartido por chat y observability.

## 8. Quality gate y archive

- [x] 8.1 Validar backend con pytest, Ruff y mypy.
- [x] 8.2 Validar frontend con Vitest, typecheck, lint y build.
- [x] 8.3 Validar OpenSpec activo y specs canonicas.
- [x] 8.4 Confirmar `git diff --check`.
