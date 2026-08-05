# Propuesta M45 — PDF + DOCX ingestion

## Why

El producto solo ingiere markdown/text/txt y HTML via URL. PDF ya se puede
descargar (allowlist de fetch) pero el pipeline lo bloquea como "no HTML".
DOCX no entra en ningun layer. Sin parsers de texto embebido no hay corpus
recuperable desde documentos de oficina reales (demo / portfolio post-v1).

## What Changes

- Parsers de **PDF (texto embebido)** y **DOCX** que producen el mismo contrato
  `ParsedDocument` → `document_versions.normalized_text`.
- **Registry** por `source_type` / content-type (no if-ladder permanente sin
  mapa).
- Authoring: tipos `pdf` y `docx` con payload binario
  `extra_metadata.content_base64` (limite alineado a fetch, 5 MiB decoded).
- URL: `application/pdf` y MIME DOCX se rutean al parser correcto tras fetch
  (allowlist DOCX en url-fetch-policy).
- CLI: `--file` opcional que lee bytes y rellena `content_base64`.
- Tests unit + integration + E2E publico: source → worker ingest+index → chat
  citations con frase distintiva del extracto.
- OpenSpec deltas en `ingestion-pipeline`, `product-authoring-surface`,
  `url-fetch-policy`.

## Fuera de alcance

- OCR / Vision / PDFs escaneados (mensaje estable "no text", job blocked).
- Unstructured, Tika, LlamaParse, PyMuPDF como default.
- PPTX / XLSX / email.
- Multipart upload API / object store / blob column (base64 en metadata o URL).
- M46 security content-guard, M48 resync UX, M50 reindex/LLM contextualize.
- Tag v1.0 o quitar `pdf_office_ingestion` del quality-gate deferred hasta
  evidencia E2E estable (opcional en closeout si el producto declara soporte).

## Impacto

API/CLI (y UI si se expone el tipo) pueden registrar PDF/DOCX, encolar
`ingest_source`, y el worker publico produce texto indexable con el path M40
existente. Chunking/embeddings no se reescriben.
