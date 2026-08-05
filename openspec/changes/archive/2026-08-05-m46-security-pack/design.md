# Diseno M46 — Security pack

## Decisiones

### 1. Content guard = redact (no block)

Redacta con `[REDACTED_SECRET]` y continua. Justificacion: demos/portfolio no
mueren por un token de ejemplo en un markdown; el secreto no queda en el
corpus. Contador en `extraction_metadata.content_guard_redactions`.

### 2. Detector compartido

`adaptive_rag.security.secrets`: patrones regex compilados (AWS AKIA…,
OpenAI-ish `sk-…`, GitHub `ghp_`/`github_pat_`, PEM BEGIN, bearer tokens
largos). API: `find_secret_spans`, `redact_secrets(text) -> (text, count)`.

### 3. Choke points

- Ingest: `IngestionPipeline._process_job` tras parse, antes de hash.
- Chat: `ChatService.respond` y `_stream_response` sobre `response.answer`
  antes de audit/delta/final.

### 4. Headers + CORS

Middleware ASGI simple siempre on. CORS: origins de settings; methods
GET/POST/PUT/PATCH/DELETE/OPTIONS; headers Authorization, Content-Type,
Accept, X-Request-Id (y los que el frontend ya use).

### 5. CI

`bandit -r src -q` y `pip-audit --strict` en job backend (o job security
separado). Test estructural M44-style asegura que el workflow los nombra.

## E2E matrix

| Path | Input | Expect |
|------|-------|--------|
| Ingest md with sk-… | authoring+worker | version sin secreto literal |
| Chat answer with secret | runner fixture | answer redacted stream+json |
| Fabricated citation id | existing | error estable |
| GET /health | any | security headers present |
| OPTIONS CORS bad origin | disallowed origin | no ACAO allow |
