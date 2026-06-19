# Propuesta M8 de hosted evals

## Why

M7 cerro el runtime minimo para Qwen live: providers opt-in, smokes separados,
usage/cost metadata y budgets por llamada. Eso prueba conectividad, pero no
mide si una corrida hosted mejora o degrada retrieval/chat con costo conocido.

El siguiente riesgo de la v1 es empezar a tomar decisiones sobre providers,
prompts o configuracion usando smokes manuales. M8 debe convertir esos smokes en
evals hosted acotados, reproducibles y seguros: mismos fixtures/versiones de
M6, mismo runtime de M7, ejecucion opt-in y reportes que unan calidad con uso y
costo.

## What Changes

- Crear el change OpenSpec `m8-live-provider-evals-plan`.
- Definir una secuencia M8 que entregue:
  `m8-hosted-eval-contract`, `m8-live-retrieval-eval-runner`,
  `m8-live-chat-eval-runner`, `m8-evals-cli-hosted-mode` y
  `m8-quality-gate`.
- Introducir la capacidad `hosted-evals` sobre `evals-baseline` y
  `provider-runtime`.
- Exigir que `adaptive-rag evals run` siga siendo offline y sin red por
  defecto.
- Exigir un modo hosted explicito, con credenciales via environment, presupuesto
  maximo de corrida, inputs pequenos y reportes JSON con quality metrics,
  provider usage y costo estimado.
- Exigir que los tests sigan usando clientes fake/monkeypatch y no requieran
  credenciales live.
- Mantener dashboards, LLM-as-judge hosted, streaming, persistencia de
  conversaciones, rerank live y tuning automatico fuera de este milestone.
- Actualizar `docs/progress.md` y `docs/roadmap.md` para reflejar M8 activo y
  el siguiente slice recomendado.

## Capacidades

### Capacidades nuevas

- `hosted-evals`

### Capacidades modificadas

- Ninguna. M8 consume `evals-baseline` y `provider-runtime` sin cambiar sus
  contratos publicos existentes.

## Impacto

- Agrega un change activo bajo `openspec/changes/`.
- Actualiza docs de progreso/roadmap.
- No agrega migraciones Alembic ni codigo productivo en este PR.
- No requiere credenciales live para validar este PR de planificacion.
- La implementacion posterior tocara `adaptive_rag.evals`, CLI de evals,
  factories/runtime de providers, reportes JSON y tests con fakes de cliente.

