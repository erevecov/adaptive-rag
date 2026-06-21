# Arquitectura

Esta carpeta contiene lineas base de arquitectura y producto que orientan varios
changes OpenSpec.

Documentos:

- `v1-design.md`: linea base de arquitectura y alcance v1.
- `retrieval-decision-gates.md`: criterios para abrir o rechazar futuros
  experimentos de lexical/RRF, sparse retrieval o tuning de retrieval.
- `retrieval-strategy-decision.md`: decision M11 para ejecutar primero tuning
  de `candidate_limit` y mantener lexical/RRF y Qwen sparse en hold.
- `candidate-limit-ab-evidence.md`: evidencia M11 del runner A/B offline y
  decision de mantener la superficie API/CLI de candidate tuning en hold.
- `retrieval-evidence-expansion.md`: decision M12 para ampliar evidencia sobre
  distractors y lexical misses antes de abrir nuevas estrategias de retrieval.
- `retrieval-strategy-refresh-m12.md`: evidencia M12 actualizada y decision de
  mantener dense default sin promover candidate tuning, lexical/RRF ni sparse.
- `chat-audit-trail-m13.md`: decision M13 para persistir sesiones, mensajes,
  tool calls, retrieval runs, citations y usage/cost antes de streaming,
  dashboards o historial.
- `chat-history-m14.md`: decision M14 para exponer listado/detalle read-only de
  sesiones antes de frontend, streaming o dashboards.

Reglas:

- OpenSpec manda para contratos implementados o en implementacion.
- Estos documentos pueden explicar contexto, tradeoffs y direccion de producto.
- No se usan para tracking de tareas ni para registrar progreso diario.
- Si una decision arquitectonica se convierte en trabajo ejecutable, debe pasar
  por `openspec/changes/<change-id>/`.
