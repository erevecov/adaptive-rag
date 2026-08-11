# Runbook de la plataforma PostgreSQL de jobs

Esta es la guía operativa de la cola general de Adaptive RAG. PostgreSQL es el
único broker: persiste jobs, intentos, eventos, límites, schedules y presencia
de workers. La entrega es `at-least-once`; los handlers con efectos externos
deben usar la clave de idempotencia y comprobar `context.is_lease_healthy()`
antes de publicar el efecto.

## Puesta en marcha

1. Configurar `ADAPTIVE_RAG_DATABASE_URL` para API y
   `ADAPTIVE_RAG_JOB_DATABASE_URL` para worker/scheduler.
2. Aplicar la única cabeza Alembic antes de iniciar procesos:

   ```bash
   uv run alembic heads
   uv run alembic upgrade head
   ```

3. Iniciar el stack global. Ningún servicio requiere fijar un workspace:

   ```bash
   docker compose up --build postgres api scheduler
   docker compose --profile worker up --build worker
   ```

   Para ejecución local o capacidad explícita:

   ```bash
   uv run adaptive-rag jobs worker \
     --queues ingestion,default,system \
     --concurrency 8 \
     --poll-interval-seconds 5 \
     --drain-timeout-seconds 30
   uv run adaptive-rag jobs scheduler --poll-interval-seconds 30
   ```

`SIGTERM`/`SIGINT` lleva al worker a `draining`, espera hasta el timeout y deja
que el reaper recupere cualquier intento sin finalizar. `LISTEN/NOTIFY` reduce
latencia, pero el polling es el mecanismo de recuperación y no puede apagarse.

## Rol de base de datos con mínimo privilegio

El rol del worker no debe ser owner, ejecutar Alembic ni tener `CREATE`. Ajustar
la lista adicional a las tablas que realmente usan los handlers registrados:

```sql
CREATE ROLE adaptive_rag_worker LOGIN PASSWORD '<secret-managed-externally>';
GRANT CONNECT ON DATABASE adaptive_rag TO adaptive_rag_worker;
GRANT USAGE ON SCHEMA public TO adaptive_rag_worker;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  job_queues, job_queue_workspace_state, jobs, job_attempts,
  job_events, job_workers
TO adaptive_rag_worker;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  workspaces, sources, documents, document_versions, chunks
TO adaptive_rag_worker;
```

No conceder `CREATE ON SCHEMA`, ownership, superuser ni escritura sobre
`alembic_version`. Si un handler necesita otra tabla, agregar sólo sus permisos
DML; el proceso debe fallar cerrado hasta que ese grant exista.

## Operación cotidiana

Inspección:

```bash
uv run adaptive-rag jobs list --system --status queued --queue default
uv run adaptive-rag jobs list --workspace-id <uuid> --status dead_letter
uv run adaptive-rag jobs show --system --job-id <uuid>
uv run adaptive-rag jobs workers list
uv run adaptive-rag jobs queues list
```

La consola web `Settings > Background Jobs` ofrece Jobs y Schedules a lectores
del workspace. Queues, Workers y métricas globales son sólo para superadmins.
Los filtros están en la URL; los detalles muestran payload/resultados ya
redactados, intentos y eventos.

Pausar una cola detiene nuevos claims, no aborta intentos en curso:

```bash
uv run adaptive-rag jobs queues pause --queue default --version <n>
uv run adaptive-rag jobs queues configure --queue default --version <n> \
  --global-concurrency-limit 16 --workspace-concurrency-limit 8 \
  --default-lease-seconds 300
uv run adaptive-rag jobs queues resume --queue default --version <n>
```

Las mutaciones usan versión optimista. Ante conflicto, volver a leer el recurso
y decidir con su estado actual; no repetir con una versión inventada.

## Fallos, retries y fencing

- `blocked`: dependencia o dato requiere intervención; corregir y ejecutar
  `jobs unblock`.
- `dead_letter`: agotó retries o tuvo una falla permanente; inspeccionar los
  intentos y ejecutar `jobs retry` sólo después de corregir la causa.
- `running` con lease vencido: el reaper expira exactamente el intento actual,
  incrementa retry y lo reencola o lo envía a dead letter.
- `fenced_write_rejected`: un worker obsoleto quiso completar/renovar/progresar
  después de perder su intento. Es evidencia de que el fence protegió el job,
  no motivo para sobrescribir el resultado actual.

```bash
uv run adaptive-rag jobs unblock --system --job-id <uuid> --version <n>
uv run adaptive-rag jobs retry --workspace-id <uuid> --job-id <uuid> --version <n>
uv run adaptive-rag jobs cancel --workspace-id <uuid> --job-id <uuid> --version <n>
```

Para un worker stale, comprobar heartbeat, `locked_until`, intento actual y
eventos. No editar filas manualmente. Mantener otro worker/reaper activo; tras
vencer el lease el job se recupera. Muchos rechazos de fencing indican pausas
largas, heartbeats bloqueados, lease demasiado corto o procesos duplicados.

## Schedules, misfires y zonas horarias

Los schedules guardan cron e IANA timezone. El cálculo distingue DST y persiste
la ocurrencia programada para deduplicarla. `skip` omite ejecuciones perdidas;
`run_once` materializa una; `catch_up` materializa hasta `max_catch_up`.

```bash
uv run adaptive-rag jobs schedules list --system
uv run adaptive-rag jobs schedules run-now --system \
  --schedule-id <uuid> --version <n>
uv run adaptive-rag jobs schedules pause --system \
  --schedule-id <uuid> --version <n>
uv run adaptive-rag jobs scheduler --once
```

Si aumenta `scheduler_lag_seconds` o `scheduler_misfires`, comprobar que existe
un scheduler live, la timezone es válida y `next_run_at` avanza. Dos schedulers
son seguros: locks y claves de ocurrencia impiden materialización duplicada.

## Métricas y alertas mínimas

`GET /admin/job-metrics` entrega snapshots acotados de:

- profundidad y edad del job elegible más antiguo por cola;
- ejecución por handler/workspace y capacidad configurada;
- p50/p95/máximo de enqueue-a-start y duración de intento (muestra 10.000);
- retries, blocks, dead letters, cancelaciones, leases vencidos y fencing;
- workers live/stale/draining, trabajo sin ruta y lag/misfires del scheduler.

Alertar por edad elegible sostenida, `unroutable_queued > 0`, dead letters,
workers stale, lag creciente y una tasa anormal de leases vencidos/fencing.

## Retención

El default conserva succeeded/cancelled 30 días y dead-letter 90 días. Sólo
borra lotes acotados de jobs terminales sin referencia en provider usage;
attempts/eventos caen en la misma transacción. Siempre previsualizar:

```bash
uv run adaptive-rag jobs retention --batch-size 1000
uv run adaptive-rag jobs retention --batch-size 1000 --apply
```

Repetir hasta `candidate_jobs = 0`. El dry-run no muta. Hacer backup y conservar
artefactos de auditoría externos según la política del entorno antes de aplicar.

## Rollback y compatibilidad

El rollback de aplicación puede detener worker/scheduler y volver a la imagen
anterior mientras la migración siga aplicada. No ejecutar `alembic downgrade`
con jobs nuevos: eliminaría schedules, intentos, presencia y fencing. Restaurar
la base desde backup es la única reversión segura después de aceptar trabajo.

Los comandos `jobs run-worker`, `enqueue-ingest-source`, `system run-scheduler`
y las superficies antiguas de ingestion se mantienen como adaptadores de
compatibilidad. Para nueva operación usar `jobs worker`, `jobs scheduler` y el
control plane general.

## Smoke de despliegue

```bash
docker compose up -d postgres
docker compose run --rm api uv run alembic upgrade head
docker compose run --rm worker adaptive-rag jobs worker --once
docker compose run --rm scheduler adaptive-rag jobs scheduler --once
docker compose down
```

`docker compose down` conserva el volumen. `down -v` borra datos y requiere una
decisión destructiva separada.
