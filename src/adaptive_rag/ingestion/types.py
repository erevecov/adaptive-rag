"""Tipos compartidos del pipeline de ingestion."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

# Cap on text extracted from binary documents (PDF/DOCX). A 5 MiB payload of
# highly compressible content can decompress into gigabytes of text; without
# a cap that turns into worker memory pressure and oversized document rows.
MAX_EXTRACTED_TEXT_CHARS: Final[int] = 8 * 1024 * 1024


class IngestionPipelineError(ValueError):
    """Error no retryable de ingestion."""


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    normalized_text: str
    parser_metadata: Mapping[str, Any]
    extraction_metadata: Mapping[str, Any]


def normalize_text(content: str) -> str:
    """Normaliza line endings y whitespace exterior sin cambiar el cuerpo."""

    return content.replace("\r\n", "\n").replace("\r", "\n").strip()
