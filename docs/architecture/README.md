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

Reglas:

- OpenSpec manda para contratos implementados o en implementacion.
- Estos documentos pueden explicar contexto, tradeoffs y direccion de producto.
- No se usan para tracking de tareas ni para registrar progreso diario.
- Si una decision arquitectonica se convierte en trabajo ejecutable, debe pasar
  por `openspec/changes/<change-id>/`.
