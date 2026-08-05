"""Registry de parsers binarios por source_type y content-type."""

from __future__ import annotations

from typing import Protocol

from adaptive_rag.ingestion.parsers.docx import DocxTextParser
from adaptive_rag.ingestion.parsers.pdf import PdfEmbeddedTextParser
from adaptive_rag.ingestion.types import ParsedDocument

PDF_CONTENT_TYPE = "application/pdf"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)

BINARY_SOURCE_TYPES = frozenset({"pdf", "docx"})


class BinaryDocumentParser(Protocol):
    def parse(self, content: bytes) -> ParsedDocument:
        """Extrae texto normalizado desde bytes del documento."""


_DEFAULT_PDF = PdfEmbeddedTextParser()
_DEFAULT_DOCX = DocxTextParser()

_CONTENT_TYPE_PARSERS: dict[str, BinaryDocumentParser] = {
    PDF_CONTENT_TYPE: _DEFAULT_PDF,
    DOCX_CONTENT_TYPE: _DEFAULT_DOCX,
}

_SOURCE_TYPE_PARSERS: dict[str, BinaryDocumentParser] = {
    "pdf": _DEFAULT_PDF,
    "docx": _DEFAULT_DOCX,
}


def parser_for_content_type(content_type: str) -> BinaryDocumentParser | None:
    return _CONTENT_TYPE_PARSERS.get(content_type)


def parser_for_source_type(source_type: str) -> BinaryDocumentParser | None:
    return _SOURCE_TYPE_PARSERS.get(source_type)
