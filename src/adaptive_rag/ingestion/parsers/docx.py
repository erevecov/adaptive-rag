"""Extractor de texto de documentos DOCX (OOXML)."""

from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.opc.exceptions import PackageNotFoundError

from adaptive_rag.ingestion.types import (
    IngestionPipelineError,
    ParsedDocument,
    normalize_text,
)

PARSER_NAME = "docx_text"
PARSER_VERSION = "docx_text_v1"


class DocxTextParser:
    """Parser determinista de parrafos y celdas de tabla via python-docx."""

    parser_version = PARSER_VERSION

    def parse(self, content: bytes) -> ParsedDocument:
        if not content:
            raise IngestionPipelineError("DOCX extraction produced no text")
        try:
            document = Document(BytesIO(content))
        except PackageNotFoundError as exc:
            raise IngestionPipelineError(
                "DOCX content is not a readable DOCX package"
            ) from exc
        except Exception as exc:
            raise IngestionPipelineError(
                "DOCX content is not a readable DOCX package"
            ) from exc

        parts: list[str] = []
        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if text:
                parts.append(text)
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))

        normalized = normalize_text("\n\n".join(parts))
        if not normalized:
            raise IngestionPipelineError("DOCX extraction produced no text")

        metadata: dict[str, Any] = {
            "paragraph_count": len(document.paragraphs),
            "table_count": len(document.tables),
        }
        return ParsedDocument(
            normalized_text=normalized,
            parser_metadata={
                "parser": PARSER_NAME,
                "parser_version": self.parser_version,
                "source_type": "docx",
            },
            extraction_metadata=metadata,
        )
