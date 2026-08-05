# Tasks M45 — PDF + DOCX ingestion

## 1. OpenSpec

- [x] 1.1 proposal.md / design.md / tasks.md
- [x] 1.2 Delta specs (ingestion-pipeline, product-authoring-surface, url-fetch-policy)
- [x] 1.3 `openspec change validate m45-pdf-docx-ingestion --strict`

## 2. Tests rojos (TDD)

- [x] 2.1 Fixtures minimas: PDF con texto embebido distintivo, PDF vacio/sin texto, DOCX con texto
- [x] 2.2 Unit: `PdfEmbeddedTextParser` / `DocxTextParser` happy + empty + corrupt
- [x] 2.3 Unit pipeline: URL PDF → version; URL DOCX → version; empty PDF → blocked
- [x] 2.4 Unit pipeline: source_type pdf/docx con content_base64
- [x] 2.5 Unit residual: content-type no soportado sigue bloqueando (no HTML gate message for PDF)
- [x] 2.6 Authoring: accept pdf/docx con base64; reject missing base64; reject oversize
- [x] 2.7 Integration API: create pdf/docx → enqueue → drain family → chunks
- [x] 2.8 E2E: chat citation contiene frase distintiva del PDF o DOCX

## 3. Implementacion minima

- [x] 3.1 Deps `pypdf` + `python-docx` via uv
- [x] 3.2 Parsers + registry
- [x] 3.3 Wire `_parse_source` + allowlist DOCX
- [x] 3.4 Authoring validation + CLI `--file`
- [x] 3.5 Frontend minimo (tipos + file → base64) si no bloquea
- [x] 3.6 Invertir tests que lockean "PDF no HTML"

## 4. Gates y closeout

- [x] 4.1 `uv run ruff check . && uv run mypy src && uv run pytest` (area + full viable)
- [x] 4.2 Frontend test/typecheck/lint/build si UI
- [ ] 4.3 Actualizar docs/progress.md + roadmap M45
- [ ] 4.4 Sync OpenSpec → archive
- [ ] 4.5 PR con evidencia E2E en body
