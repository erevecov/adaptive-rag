# Diseno M45 — PDF + DOCX ingestion

## Contexto

- `IngestionPipeline._parse_source` solo acepta `url`→HTML y
  `markdown|text|txt`→`BasicTextParser`.
- `URLFetchPolicy` ya permite `application/pdf` y `text/plain`; **no** DOCX.
- Tras fetch, non-HTML bloquea con
  `"URL source content type is not HTML: …"`.
- Solo se persiste `document_versions.normalized_text` (no blob original).
- M40 ya encola `index_document_version` tras ingest exitoso.

## Decisiones

### 1. Librerias livianas

| Formato | Library | Notas |
|---------|---------|--------|
| PDF | `pypdf` | Texto embebido por pagina; sin OCR |
| DOCX | `python-docx` | Walk de paragrafos + tablas basicas |

Rechazado: Unstructured (pesado), PyMuPDF (nativo innecesario en M45), OCR.

### 2. Registry por content-type / source_type

Nuevo modulo `adaptive_rag.ingestion.parsers` con:

- Protocolo `BinaryDocumentParser.parse(content: bytes) -> ParsedDocument`
- `PdfEmbeddedTextParser` (`parser=pdf_embedded`, version `pdf_embedded_v1`)
- `DocxTextParser` (`parser=docx_text`, version `docx_text_v1`)
- Mapa `CONTENT_TYPE_PARSERS` y `SOURCE_TYPE_BINARY = {pdf, docx}`

`_parse_source`:

1. `url` → fetch → dispatch por content-type base:
   - HTML/XHTML → Trafilatura (existente)
   - `application/pdf` → PDF parser
   - DOCX MIME → DOCX parser
   - otro allowlisted sin parser → block estable
2. `markdown|text|txt` → BasicTextParser (sin cambio)
3. `pdf|docx` → decode `content_base64` → mismo parser binario
4. else → Unsupported

### 3. Representacion de sources tipadas

- `source_type`: `pdf` | `docx` (ademas de los cuatro existentes).
- Payload requerido: `extra_metadata.content_base64` (string base64 estandar,
  no URL-safe requerido; padding opcional tolerado).
- Limite: bytes decodificados ≤ `max_response_bytes` del fetch policy (5 MiB).
- Opcional: `extra_metadata.filename` (solo metadata de extraccion).
- No se retiene el binario en `document_versions`; solo texto normalizado.

### 4. Texto vacio / PDF escaneado

Si el extracto strip() es vacio → `IngestionPipelineError` con mensaje estable:

- `"PDF extraction produced no text"`
- `"DOCX extraction produced no text"`

Job **blocked** (mismo patron que HTML vacio). **Sin OCR.**

### 5. URL PDF/DOCX en scope

Fetch allowlist: mantener PDF; agregar

`application/vnd.openxmlformats-officedocument.wordprocessingml.document`

No se agrega `application/msword` legacy (.doc) en M45.

### 6. CLI

`sources create --file PATH` lee bytes, base64-encode a
`extra_metadata.content_base64`. Incompatible con `--content` de texto en el
mismo comando para tipos binarios (error claro).

### 7. Frontend (minimo)

Exponer `pdf`/`docx` en el select de authoring y un input `type=file` que
rellena `content_base64` en el body de create. Si el PR de UI se vuelve ruidoso,
API+CLI bastan para el E2E de standing order, pero se intenta UI minima.

### 8. Quality-gate deferred flag

`pdf_office_ingestion` puede permanecer en deferred hasta closeout con E2E;
quitarlo solo si se agrega un smoke opcional o el producto declara el path
como default. Preferencia M45: **dejar deferred** y documentar en progress
(no inflar quality-gate).

## Alternativas rechazadas

- **Solo URL, sin tipos pdf/docx:** deja fuera archivos locales sin host.
- **Solo base64, sin URL parse:** desperdicia el half-open del fetch PDF.
- **Extract en authoring create:** saltea worker/auditoria y duplica logica.
- **Multipart + blob store:** scope de storage; postergado.
- **Sniff magic-bytes siempre:** util como edge; M45 confia en content-type /
  source_type declarados; corrupt bytes fallan en el parser.

## Riesgos

| Riesgo | Mitigacion |
|--------|------------|
| Base64 infla JSONB | Cap 5 MiB decoded; documentar URL para archivos grandes |
| PDF sin texto embebido | Block + mensaje; sin OCR |
| Layout jumbled de pypdf | Aceptable; chunker plain-text |
| CVE parsers PDF | Cap de bytes; no cargar recursos remotos del PDF |
| Tests que asumen PDF bloqueado | Invertir fixture a happy path + residual non-supported CT |

## E2E matrix (done criteria)

| Actor | create | enqueue/run worker | chat citation |
|-------|--------|--------------------|---------------|
| API pdf base64 | 201 | ingest+index succeeded | frase del PDF |
| API docx base64 | 201 | same | frase del DOCX |
| URL pdf | 201 source url | same | frase del PDF |
| Fail empty PDF | create ok | job blocked, no version indexable | n/a |
| Edge unsupported type | 422 authoring | — | — |
| Edge wrong CT URL | — | blocked, no HTML extractor | — |

## Dependencias de codigo (must-touch)

- `src/adaptive_rag/ingestion/pipeline.py`
- `src/adaptive_rag/ingestion/parsers/` (nuevo)
- `src/adaptive_rag/ingestion/url_fetch_policy.py`
- `src/adaptive_rag/authoring.py`
- `src/adaptive_rag/cli/sources.py`
- `pyproject.toml` / `uv.lock`
- tests unit/integration + fixtures
- frontend authoring (minimo)
