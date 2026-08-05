"""CLI --file support for pdf/docx sources."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from adaptive_rag.authoring import AuthoringError
from adaptive_rag.cli.sources import _extra_metadata_from_inputs

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "m45"


def test_file_option_encodes_pdf_bytes() -> None:
    path = FIXTURES / "sample.pdf"
    metadata = _extra_metadata_from_inputs(
        source_type="pdf",
        content=None,
        file_path=path,
    )
    assert metadata is not None
    assert metadata["filename"] == "sample.pdf"
    assert base64.b64decode(metadata["content_base64"]) == path.read_bytes()


def test_file_and_content_are_mutually_exclusive() -> None:
    with pytest.raises(AuthoringError, match="either --content or --file"):
        _extra_metadata_from_inputs(
            source_type="pdf",
            content="nope",
            file_path=FIXTURES / "sample.pdf",
        )


def test_file_rejected_for_text_source_types() -> None:
    with pytest.raises(AuthoringError, match="only valid for pdf or docx"):
        _extra_metadata_from_inputs(
            source_type="markdown",
            content=None,
            file_path=FIXTURES / "sample.pdf",
        )
