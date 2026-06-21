# Diseno M17 de observability de chat y costo-latencia

## Contexto

M13 agrego audit trail durable de chat. M14 expuso historial read-only. M15
agrego frontend inicial y M16 agrego streaming SSE. El sistema ya puede
responder preguntas, persistir sesiones, tool calls, retrieval runs y registrar
usage/cost de providers.

La brecha actual es operativa: para una demo o uso local no hay una forma
directa de ver costo, latencia, volumen y fallos agregados por proyecto. La
release v1.0 de portafolio necesita un reporte reproducible de
calidad/costo/latencia; M17 debe aportar el bloque costo/latencia sin construir
un dashboard avanzado.

## Decision

La decision recomendada es `proceed` con M17 como superficie read-only de
observability local-first:

- backend agrega read models y queries sobre `chat_sessions`, `tool_calls`,
  `retrieval_runs` y `provider_usage`;
- API expone un endpoint de resumen por proyecto bajo la superficie de chat;
- CLI expone un comando equivalente con JSON estable;
- los agregados se calculan desde datos existentes, sin tablas nuevas al
  inicio;
- no se agrega frontend ni dashboard en M17; una UI puede venir despues de
  fijar el contrato backend/CLI.

Esta decision mantiene el alcance acotado y reutiliza el audit trail como fuente
de verdad.

## Objetivos

- Resumir sesiones de chat por proyecto y status.
- Resumir provider usage por operation/provider/model.
- Reportar costo estimado conocido, tokens/unidades conocidas y conteo de
  registros con costo o usage ausente.
- Reportar latencia con metricas portables: count, min, avg, max y percentiles
  calculados en Python cuando sea necesario.
- Reportar errores agregados sin exponer secretos ni raw payloads.
- Mantener API y CLI equivalentes para automatizar demos/reportes.
- Mantener tests deterministas sobre SQLite y fakes locales.

## No objetivos

- No agregar dashboard avanzado ni visualizaciones nuevas.
- No agregar frontend en M17.
- No agregar OpenTelemetry, Langfuse ni exporters.
- No agregar nuevas tablas ni materialized views en el primer slice.
- No mutar sesiones, mensajes, tool calls, retrieval runs ni provider usage.
- No guardar prompts completos, respuestas completas, raw provider payloads ni
  API keys en el resumen.
- No cambiar retrieval, rerank, providers, streaming ni historial.
- No agregar replay, delete, edit, retention ni auth final.

## Contrato recomendado

### Endpoint HTTP

```text
GET /projects/{project_id}/chat/observability/summary
```

Query params opcionales:

- `created_at_from`: ISO datetime inclusivo.
- `created_at_to`: ISO datetime exclusivo.
- `status`: filtro opcional de status de sesion (`running`, `succeeded`,
  `failed`).

Sin fechas, el resumen cubre todos los datos persistidos del proyecto. Esto
evita defaults dependientes del reloj y mantiene tests deterministas.

### CLI

```text
adaptive-rag chat observability summary --project-id <uuid>
adaptive-rag chat observability summary --project-id <uuid> --created-at-from <iso> --created-at-to <iso>
```

La salida debe ser JSON estable equivalente al endpoint HTTP.

### Shape de respuesta

El shape publico debe separar conteos, latencias y costos:

```json
{
  "project_id": "<uuid>",
  "filters": {
    "created_at_from": null,
    "created_at_to": null,
    "status": null
  },
  "sessions": {
    "total": 12,
    "by_status": {
      "running": 0,
      "succeeded": 10,
      "failed": 2
    }
  },
  "provider_usage": {
    "total_records": 18,
    "total_estimated_cost_usd": 0.1234,
    "missing_cost_count": 1,
    "groups": [
      {
        "operation": "chat",
        "provider": "qwen",
        "model": "qwen-plus",
        "record_count": 8,
        "estimated_cost_usd": 0.08,
        "input_tokens": 1200,
        "output_tokens": 640,
        "total_tokens": 1840,
        "input_count": null,
        "latency_ms": {
          "count": 8,
          "min": 120,
          "avg": 220.5,
          "p50": 210,
          "p95": 410,
          "max": 420
        }
      }
    ]
  },
  "errors": {
    "session_error_count": 2,
    "provider_error_count": 1,
    "top_messages": [
      {
        "message": "runner failed",
        "count": 2
      }
    ]
  }
}
```

Reglas:

- `total_estimated_cost_usd` suma solo costos conocidos.
- `missing_cost_count` cuenta records sin costo estimado.
- Tokens/unidades ausentes no se inventan; quedan `null` en grupos sin datos.
- Percentiles se calculan sobre valores de latencia conocidos.
- `top_messages` debe truncar mensajes a una longitud segura y agrupar por el
  mensaje estable persistido.
- El resumen nunca devuelve mensajes completos de usuario/assistant, prompts
  completos ni raw provider payloads.

## Secuencia recomendada de M17

### 1. `m17-chat-observability`

Alcance:

- Crear el change OpenSpec M17.
- Documentar contrato API/CLI, agregados y slices.
- Actualizar progress/roadmap y arquitectura.

Fuera de alcance:

- Codigo productivo backend/frontend.

### 2. `m17-observability-read-models`

Alcance:

- Agregar read models y repository methods para el resumen.
- Cubrir filtros por proyecto, status y fechas.
- Calcular latencias y percentiles de forma portable.
- Agregar tests unitarios/repository con datos deterministas.

Fuera de alcance:

- API, CLI y frontend.

### 3. `m17-observability-api`

Alcance:

- Agregar schema HTTP y endpoint
  `GET /projects/{project_id}/chat/observability/summary`.
- Mapear filtros invalidos a errores estables.
- Probar aislamiento por proyecto y shape JSON.

Fuera de alcance:

- Dashboard o visualizaciones.

### 4. `m17-observability-cli`

Alcance:

- Agregar comando `adaptive-rag chat observability summary`.
- Reutilizar el mismo read model que la API.
- Emitir JSON equivalente.

Fuera de alcance:

- Reportes HTML, CSV o UI.

### 5. `m17-quality-gate`

Alcance:

- Validar Python, OpenSpec y docs.
- Archivar el change M17 al completar el milestone.

## Riesgos y mitigaciones

- Riesgo: convertir M17 en dashboard avanzado.
  Mitigacion: M17 solo fija API/CLI read-only y JSON estable.
- Riesgo: duplicar calculos entre API y CLI.
  Mitigacion: read model compartido en repository/service.
- Riesgo: queries no portables entre SQLite y Postgres.
  Mitigacion: usar queries simples y calcular percentiles en Python.
- Riesgo: exponer datos sensibles por error.
  Mitigacion: resumen solo agrega conteos, costos, latencias y mensajes de
  error estables/truncados.
- Riesgo: sumar costos incompletos como si fueran totales exactos.
  Mitigacion: reportar `missing_cost_count` y no inventar valores ausentes.

## Validacion esperada por slice

Planificacion:

```text
pnpm dlx @fission-ai/openspec validate m17-chat-observability --strict
pnpm dlx @fission-ai/openspec validate --specs --strict
pnpm dlx @fission-ai/openspec list
git diff --check
```

Implementacion posterior:

```text
uv run pytest
uv run ruff check .
uv run mypy src
```

Si un slice posterior toca frontend, tambien debe validar:

```text
pnpm --dir frontend test
pnpm --dir frontend lint
pnpm --dir frontend build
```
