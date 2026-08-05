# Propuesta M46 — Security pack

## Why

El producto local expone API/chat/ingestion sin content-guard de secretos en
texto de corpus ni filtros de salida en respuestas. CORS permite origins
locales pero methods/headers son wildcards, y no hay security headers de
respuesta. Controles sin tests/CI son teatro (leccion beflow).

## What Changes

- **Content guard** heuristico en ingesta: detecta patrones de secretos en
  `normalized_text` y **redacta** con placeholder estable antes de hash y
  persistencia (metadata de redacciones).
- **Filtro de salida** en chat non-stream y stream: redaccion del `answer`
  (y consistencia con audit); citas fabricadas siguen fallando via
  `_resolve_citations` (IDs no recuperados).
- **Security headers** en API (`X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`) + CORS con methods/headers explicitos.
- **Tests unit/integration** + pasos bandit/pip-audit en CI workflow.
- OpenSpec capability `security-pack` + deltas ingestion/chat-streaming.

## Fuera de alcance

- DLP SaaS, WAF, CSP de producto completa, HSTS (sin TLS asumido en local).
- OCR/PDF secrets en imagenes, retro-scan de corpus historico (lifecycle).
- OAuth/SSO, multi-tenant, sharing publico.
- Token streaming word-by-word (el path actual emite answer completo).
- Tag v1.0.

## Impacto

Corpus nuevo no indexa secretos literales detectados; clientes de chat no
reciben secretos heuristicos en answers; browser/API clients ven headers
baseline y CORS acotado; CI ejecuta scanners de seguridad basicos.
