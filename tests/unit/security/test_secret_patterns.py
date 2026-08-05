"""Unit tests for heuristic secret detection/redaction."""

from __future__ import annotations

from adaptive_rag.security.secrets import REDACTION_MARKER, redact_secrets


def test_redacts_openai_style_key() -> None:
    text = "token sk-proj-abcdefghijklmnopqrstuvwxyz012345 and more"
    redacted, count = redact_secrets(text)
    assert count == 1
    assert "sk-proj-" not in redacted
    assert REDACTION_MARKER in redacted
    assert "and more" in redacted


def test_redacts_aws_access_key() -> None:
    text = "key AKIAIOSFODNN7EXAMPLE here"
    redacted, count = redact_secrets(text)
    assert count == 1
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert REDACTION_MARKER in redacted


def test_redacts_github_pat() -> None:
    text = "auth ghp_abcdefghijklmnopqrstuvwx here"
    redacted, count = redact_secrets(text)
    assert count == 1
    assert "ghp_" not in redacted


def test_redacts_pem_block() -> None:
    text = (
        "before\n"
        "-----BEGIN PRIVATE KEY-----\n"
        "MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC\n"
        "-----END PRIVATE KEY-----\n"
        "after"
    )
    redacted, count = redact_secrets(text)
    assert count == 1
    assert "BEGIN PRIVATE KEY" not in redacted
    assert "before" in redacted and "after" in redacted


def test_clean_text_unchanged() -> None:
    text = "Adaptive RAG indexes markdown without secrets."
    redacted, count = redact_secrets(text)
    assert count == 0
    assert redacted == text
