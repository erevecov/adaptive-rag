"""Unit tests for PDF/DOCX embedded-text parsers (M45)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from docx import Document
from pypdf import PdfWriter

import adaptive_rag.ingestion.parsers.docx as docx_module
import adaptive_rag.ingestion.parsers.pdf as pdf_module
from adaptive_rag.ingestion.parsers import (
    DocxTextParser,
    PdfEmbeddedTextParser,
    parser_for_content_type,
    parser_for_source_type,
)
from adaptive_rag.ingestion.parsers.registry import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE
from adaptive_rag.ingestion.types import IngestionPipelineError

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "m45"
SAMPLE_PDF = (FIXTURES / "sample.pdf").read_bytes()
EMPTY_PDF = (FIXTURES / "empty_text.pdf").read_bytes()
SAMPLE_DOCX = (FIXTURES / "sample.docx").read_bytes()


def test_pdf_parser_extracts_embedded_text_from_fixture() -> None:
    parsed = PdfEmbeddedTextParser().parse(SAMPLE_PDF)

    assert "ALPHA-PDF-442" in parsed.normalized_text
    assert parsed.parser_metadata["parser"] == "pdf_embedded"
    assert parsed.parser_metadata["parser_version"] == "pdf_embedded_v1"
    assert parsed.extraction_metadata["page_count"] == 1
    assert parsed.extraction_metadata["pages_with_text"] == 1


def test_pdf_parser_blocks_when_no_embedded_text() -> None:
    with pytest.raises(IngestionPipelineError, match="PDF extraction produced no text"):
        PdfEmbeddedTextParser().parse(EMPTY_PDF)


def test_pdf_parser_blocks_corrupt_bytes() -> None:
    with pytest.raises(IngestionPipelineError, match="not a readable PDF"):
        PdfEmbeddedTextParser().parse(b"not-a-pdf-payload")


def test_pdf_parser_blocks_broken_page_tree() -> None:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buffer)
    broken = buffer.getvalue().replace(b"/Pages", b"/Xages")
    with pytest.raises(IngestionPipelineError, match="not a readable PDF"):
        PdfEmbeddedTextParser().parse(broken)


def test_pdf_parser_blocks_excessive_extracted_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pdf_module, "MAX_EXTRACTED_TEXT_CHARS", 8)
    with pytest.raises(IngestionPipelineError, match="exceeds max size"):
        PdfEmbeddedTextParser().parse(SAMPLE_PDF)


def test_docx_parser_extracts_paragraphs_from_fixture() -> None:
    parsed = DocxTextParser().parse(SAMPLE_DOCX)

    assert "ALPHA-DOCX-991" in parsed.normalized_text
    assert "Second paragraph" in parsed.normalized_text
    assert parsed.parser_metadata["parser"] == "docx_text"
    assert parsed.parser_metadata["parser_version"] == "docx_text_v1"


def test_docx_parser_blocks_when_empty() -> None:
    buffer = BytesIO()
    Document().save(buffer)
    with pytest.raises(
        IngestionPipelineError, match="DOCX extraction produced no text"
    ):
        DocxTextParser().parse(buffer.getvalue())


def test_docx_parser_blocks_corrupt_bytes() -> None:
    with pytest.raises(IngestionPipelineError, match="not a readable DOCX"):
        DocxTextParser().parse(b"PK\x03\x04not-a-real-docx")


def test_docx_parser_blocks_excessive_extracted_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docx_module, "MAX_EXTRACTED_TEXT_CHARS", 8)
    with pytest.raises(IngestionPipelineError, match="exceeds max size"):
        DocxTextParser().parse(SAMPLE_DOCX)


def test_docx_parser_blocks_oversized_decompressed_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(docx_module, "MAX_DOCX_DECOMPRESSED_BYTES", 1)
    with pytest.raises(IngestionPipelineError, match="exceeds max decompressed size"):
        DocxTextParser().parse(SAMPLE_DOCX)


def test_registry_maps_source_and_content_types() -> None:
    assert isinstance(parser_for_source_type("pdf"), PdfEmbeddedTextParser)
    assert isinstance(parser_for_source_type("docx"), DocxTextParser)
    assert parser_for_source_type("markdown") is None
    assert isinstance(parser_for_content_type(PDF_CONTENT_TYPE), PdfEmbeddedTextParser)
    assert isinstance(parser_for_content_type(DOCX_CONTENT_TYPE), DocxTextParser)
    assert parser_for_content_type("text/plain") is None
