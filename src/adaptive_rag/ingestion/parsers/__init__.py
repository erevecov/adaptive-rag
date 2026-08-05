"""Parsers binarios de documentos para ingestion (PDF/DOCX)."""

from adaptive_rag.ingestion.parsers.binary_payload import (
    MAX_BINARY_SOURCE_BYTES,
    decode_content_base64,
)
from adaptive_rag.ingestion.parsers.docx import DocxTextParser
from adaptive_rag.ingestion.parsers.pdf import PdfEmbeddedTextParser
from adaptive_rag.ingestion.parsers.registry import (
    BINARY_SOURCE_TYPES,
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    BinaryDocumentParser,
    parser_for_content_type,
    parser_for_source_type,
)

__all__ = [
    "BINARY_SOURCE_TYPES",
    "DOCX_CONTENT_TYPE",
    "MAX_BINARY_SOURCE_BYTES",
    "PDF_CONTENT_TYPE",
    "BinaryDocumentParser",
    "DocxTextParser",
    "PdfEmbeddedTextParser",
    "decode_content_base64",
    "parser_for_content_type",
    "parser_for_source_type",
]
