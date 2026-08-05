"""Extractor de texto embebido de PDF (sin OCR)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from adaptive_rag.ingestion.types import (
    IngestionPipelineError,
    ParsedDocument,
    normalize_text,
)

PARSER_NAME = "pdf_embedded"
PARSER_VERSION = "pdf_embedded_v1"


class PdfEmbeddedTextParser:
    """Parser determinista de texto embebido via pypdf."""

    parser_version = PARSER_VERSION

    def parse(self, content: bytes) -> ParsedDocument:
        if not content:
            raise IngestionPipelineError("PDF extraction produced no text")
        try:
            reader = PdfReader(BytesIO(content), strict=False)
        except PdfReadError as exc:
            raise IngestionPipelineError("PDF content is not a readable PDF") from exc
        except Exception as exc:  # pragma: no cover - defensive
            raise IngestionPipelineError("PDF content is not a readable PDF") from exc

        page_texts: list[str] = []
        for page in reader.pages:
            try:
                extracted = page.extract_text() or ""
            except Exception as exc:  # pragma: no cover - pypdf edge cases
                raise IngestionPipelineError(
                    "PDF extraction produced no text"
                ) from exc
            if extracted.strip():
                page_texts.append(extracted)

        joined = "\n\n".join(page_texts)
        normalized = normalize_text(joined)
        if not normalized:
            raise IngestionPipelineError("PDF extraction produced no text")

        metadata: dict[str, Any] = {
            "page_count": len(reader.pages),
            "pages_with_text": len(page_texts),
        }
        return ParsedDocument(
            normalized_text=normalized,
            parser_metadata={
                "parser": PARSER_NAME,
                "parser_version": self.parser_version,
                "source_type": "pdf",
            },
            extraction_metadata=metadata,
        )
