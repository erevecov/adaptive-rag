# Propuesta M7 de provider runtime

## Why

M6 cerro evals offline sobre retrieval y chat, pero las superficies publicas
siguen usando providers/runners fake por defecto. El siguiente riesgo de la v1
es conectar providers live sin una frontera explicita de configuracion,
credenciales, limites de uso/costo, observabilidad y smokes controlados.

M7 debe introducir un runtime de providers opt-in que mantenga la experiencia
local determinista por defecto. La meta no es optimizar calidad ni agregar
streaming, sino permitir que retrieval/chat usen adapters live bajo un contrato
seguro, medible y facil de desactivar.

## What Changes

- Crear el change OpenSpec `m7-provider-runtime-plan`.
- Definir una secuencia M7 que entregue:
  `m7-provider-settings-contract`, `m7-live-embedding-provider`,
  `m7-live-chat-runner`, `m7-usage-cost-limits` y `m7-quality-gate`.
- Introducir la capacidad `provider-runtime` como contrato nuevo sobre las
  superficies canonicas de embeddings, retrieval, chat y evals.
- Exigir que fake providers/runners sigan siendo el default para tests,
  desarrollo local y evals offline.
- Exigir configuracion explicita para habilitar providers live, seleccionar
  provider/modelo y leer credenciales desde environment sin persistir secretos.
- Exigir timeouts, retries acotados, errores estables, usage/cost metadata y
  limites de gasto por request/corrida antes de llamar red en superficies
  productivas.
- Mantener streaming, hosted evals, dashboards, auth multiusuario, persistencia
  de historiales, rerank live y tuning automatico fuera de este milestone.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar M7 activo y
  el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- `provider-runtime`

### Capacidades modificadas

- Ninguna. M7 consume las specs canonicas existentes sin cambiar sus contratos
  publicos de request/response.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo en este PR.
- No requiere credenciales live para validar este PR de planificacion.
- La implementacion posterior tocara settings, factories de providers,
  adapters de embeddings/chat, usage/cost accounting, CLI/API dependencies y
  tests con fakes/monkeypatches de cliente HTTP.

