"""Tipos compartidos del pipeline de ingestion."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


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
