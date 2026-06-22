# M19 graph live evidence report

`m19-graph-live-evidence-report` consolida evidencia antes del cierre de M19.
El objetivo es unir calidad dense-vs-graph con senales operativas Neo4j live sin
promover `strategy=graph` ni cambiar `graph_store=disabled` como default.

## Superficie CLI

```bash
uv run adaptive-rag evals graph-live-evidence <suite.json> \
  --operation-report backfill.json \
  --operation-report reindex.json \
  --retrieval-smoke-report retrieval-smoke.json \
  --graph-operational-cost-usd 12.50 \
  --graph-operational-cost-notes "Neo4j Aura daily estimate"
```

`--operation-report` acepta reportes JSON emitidos por
`adaptive-rag graph backfill` y `adaptive-rag graph reindex`.
`--retrieval-smoke-report` acepta reportes JSON emitidos por
`adaptive-rag graph retrieval-smoke`. Ambos options pueden repetirse para
combinar varias corridas.

## Payload

La salida JSON conserva el reporte de calidad y agrega evidencia operacional:

- `comparison_metrics` y `comparison_cases` vienen del gate dense-vs-graph.
- `operational_metrics` agrega duracion de backfill/reindex, conteo de smokes,
  latencia promedio, fallback count/rate, errores y costo operacional.
- `error_codes` combina `error_code` de operaciones graph y `fallback_reason`
  de retrieval smoke.
- `graph_operational_cost` guarda el costo declarado en USD y una nota libre.
- `operation_reports` y `retrieval_smoke_reports` preservan los artefactos
  cargados para auditoria.

El comando sale con codigo `0` solo cuando el quality gate pasa y todos los
reportes live quedan `ready`. Cualquier operacion `failed`, smoke `fallback` o
smoke `no_results` mantiene `status=failed`.

## Alcance

- Reutiliza `run_graph_quality_gate_eval_suite(...)`.
- No ejecuta backfill, reindex ni retrieval smoke por si mismo.
- No abre una decision de promocion de defaults; solo prepara la evidencia para
  `m19-quality-gate`.
- No serializa secretos ni URIs Neo4j completas.
