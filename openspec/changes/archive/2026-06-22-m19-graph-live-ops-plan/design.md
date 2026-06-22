# Diseno M19 de graph live ops evidence

## Contexto

M18 dejo una ruta graph completa pero conservadora. Neo4j existe como backend
`graph_store=neo4j` opt-in, el grafo se materializa como indice derivado desde
Postgres, retrieval graph se solicita con `strategy=graph`, y el quality gate
offline compara dense baseline contra graph-enabled retrieval sin depender de
Neo4j live.

El cierre de M18 mantiene `dense` como default porque todavia falta evidencia
operacional: latencia de consultas graph reales, duracion de backfill,
comportamiento de reindex/stale, recuperacion ante fallos live, costo operativo
de correr Neo4j y calidad comparativa cuando la expansion graph usa el adapter
real.

M19 debe convertir la ruta Neo4j en una operacion repetible. El objetivo no es
agregar mas features de retrieval, sino probar que el indice derivado puede
crearse, reconstruirse, observarse y evaluarse contra dense de forma segura.

## Decision

La decision recomendada es `proceed` con M19 como milestone de evidencia y
operacion graph live:

- mantener `graph_store=disabled` y `strategy=dense` como defaults;
- usar Neo4j live solo bajo opt-in explicito y comandos/smokes manuales;
- definir backfill/reindex como operaciones idempotentes por `project_id`;
- medir latencia y fallback en la ruta graph con proyecciones reales `ready`;
- registrar evidencia suficiente para decidir si graph sigue en hold, avanza a
  experimento limitado, o queda no-go para promocion;
- archivar M19 solo despues de un decision gate que preserve `hold_default` si
  la evidencia no es concluyente.

## Objetivos

- Dejar una ruta local verificable para levantar Neo4j y correr smokes sin
  depender de credenciales hosted.
- Dejar una ruta managed documentada para Aura u otro endpoint `neo4j+s://`.
- Exponer una operacion CLI/API interna para backfill/reindex de una proyeccion
  graph por proyecto.
- Confirmar que backfill es idempotente, acotado por proyecto y no mezcla
  nodos/relaciones entre tenants.
- Detectar proyecciones `stale` o `pending_backfill` y bloquear retrieval graph
  hasta volver a `ready`.
- Producir reportes JSON de evidencia live con calidad, latencia, fallback,
  backfill duration, errores estables y costo operacional declarado.
- Mantener dense como default salvo que un gate posterior demuestre mejora sin
  regresiones criticas.

## No objetivos

- No promover `strategy=graph` como default en la planificacion.
- No agregar algoritmos nuevos de ranking, rerank, lexical/RRF o sparse.
- No agregar dashboard, UI, auth final ni multi-tenant admin surface.
- No convertir Neo4j en fuente durable primaria.
- No persistir secretos de Aura ni imprimir credenciales.
- No requerir Neo4j live para tests unitarios u OpenSpec validation.
- No agregar `graphdatascience` hasta tener una necesidad medida.

## Secuencia recomendada de M19

### 1. `m19-graph-live-ops-plan`

Alcance:

- Crear el change OpenSpec M19.
- Documentar objetivos, no objetivos, secuencia y gate de decision.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo backend/frontend.
- Dependencias nuevas o cambios de defaults.

### 2. `m19-neo4j-local-managed-harness`

Alcance:

- Documentar setup local con Docker o Neo4j Desktop y setup managed con URI
  cifrada.
- Agregar smoke CLI opt-in que valide settings, connectivity y errores
  estables sin exponer secretos.
- Confirmar que los smokes pueden omitirse en CI sin credenciales.

Fuera de alcance:

- Cambiar ingestion/retrieval defaults.

### 3. `m19-graph-backfill-reindex-ops`

Alcance:

- Agregar comando operativo para backfill/reindex por `project_id`.
- Marcar transiciones `pending_backfill` -> `indexing` -> `ready` o `failed`.
- Reprocesar proyecciones `stale` de forma idempotente.
- Reportar counts de nodos/relaciones, duracion y error code estable.

Fuera de alcance:

- Scheduling automatico complejo o worker distribuido.

### 4. `m19-graph-live-retrieval-smoke`

Alcance:

- Preparar fixtures/proyectos pequenos que materialicen grafo en Neo4j real.
- Ejecutar `strategy=graph` contra proyeccion `ready`.
- Validar aislamiento por proyecto, metadata filters, citations y fallback
  cuando Neo4j falla o la proyeccion deja de estar `ready`.

Fuera de alcance:

- Promocion de default.

### 5. `m19-graph-live-evidence-report`

Alcance:

- Extender el reporte dense-vs-graph para incluir latencia live, backfill
  duration, fallback counts, error codes y costo operacional declarado.
- Separar costo provider de costo graph infra para no mezclar llamadas hosted
  con operacion Neo4j.
- Serializar reportes JSON reproducibles para decision de milestone.

Fuera de alcance:

- LLM-as-judge o dashboards.

### 6. `m19-quality-gate`

Alcance:

- Ejecutar validaciones Python/OpenSpec.
- Ejecutar smokes live si hay entorno Neo4j configurado; documentar skip si no
  hay credenciales/servicio.
- Decidir `hold_default`, `limited_experiment` o `no_go_promotion`.
- Archivar el change M19 y actualizar spec canonica.

Fuera de alcance:

- Cambiar defaults sin un milestone posterior especifico.

## Gate de decision

M19 debe terminar con una decision explicita:

- `hold_default`: graph sigue opt-in porque no hay evidencia suficiente o hay
  regresiones/costo/latencia no aceptables.
- `limited_experiment`: graph puede probarse en entornos/proyectos acotados,
  con dense fallback y monitoreo, pero dense sigue default global.
- `no_go_promotion`: graph queda disponible solo para diagnostico o se pausa
  promocion por problemas operativos claros.

La decision no puede ser `promote_default` en M19. Si la evidencia justifica
considerarlo, debe abrirse un M20 dedicado a rollout/defaults con criterios de
seguridad, rollback y observability.

## Validacion esperada por slice

Planificacion:

```text
pnpm dlx @fission-ai/openspec validate m19-graph-live-ops-plan --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

Implementacion posterior:

```text
uv run pytest
uv run ruff check src tests
uv run mypy src/adaptive_rag
```

Si un slice posterior toca frontend, tambien debe validar:

```text
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```
