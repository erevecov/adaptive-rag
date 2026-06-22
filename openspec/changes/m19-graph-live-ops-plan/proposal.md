# Propuesta M19 de graph live ops evidence

## Why

M18 cerro la integracion inicial de Neo4j como graph DB opt-in: contrato
`GraphStore`, adapter live, indexer, ruta `strategy=graph` y un quality gate
offline dense-vs-graph. La decision de cierre fue conservadora:
`hold_default`. `dense` sigue como default y graph retrieval queda disponible
solo para experimentos controlados.

El siguiente riesgo ya no es demostrar que la ruta existe, sino confirmar que
puede operarse con Neo4j real sin degradar el producto: setup local/managed,
backfill/reindex idempotente, estados `stale`/`pending_backfill`, latencia,
fallos, costo operativo y evidencia de calidad con graph store live. M19 debe
cerrar esa brecha antes de considerar cualquier promocion de defaults.

La opcion recomendada es abrir un milestone de evidencia/operacion graph live,
no una promocion de `strategy=graph`. Esto mantiene el sistema conservador,
preserva Postgres como fuente durable y convierte Neo4j en una ruta medible y
operable antes de ampliar su uso.

## What Changes

- Crear el change OpenSpec `m19-graph-live-ops-plan`.
- Extender la capacidad `graph-store` para exigir:
  - smoke local/managed de Neo4j live sin secretos en logs;
  - backfill/reindex operable, idempotente y acotado por `project_id`;
  - manejo explicito de proyecciones `pending_backfill`, `indexing`, `ready`,
    `stale` y `failed`;
  - reportes de evidencia live con calidad, latencia, fallback y costo
    operacional;
  - decision gate conservador antes de cambiar defaults.
- Definir la secuencia M19 para:
  - documentar el harness local/managed;
  - agregar comandos operativos de backfill/reindex;
  - ejecutar smoke/evals con Neo4j real;
  - producir un reporte comparativo y una decision de default.
- Actualizar `docs/progress.md`, `docs/roadmap.md` y arquitectura con M19
  activo.

## Capacidades

### Capacidades modificadas

- `graph-store`

### Capacidades nuevas

- Ninguna.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Agrega una nota de arquitectura para M19.
- Actualiza docs de progreso/roadmap.
- Este PR de planificacion no cambia codigo productivo Python, frontend,
  settings, dependencias, migrations ni infraestructura.
- No cambia `strategy=dense` como default.
- No requiere Neo4j live para validar este PR de planificacion.
