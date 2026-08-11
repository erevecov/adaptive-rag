"""Stable API error helper coverage."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from adaptive_rag.api.errors import DEFAULT_API_ERROR_MESSAGES, raise_api_error


def test_raise_api_error_includes_default_message_for_known_codes() -> None:
    with pytest.raises(HTTPException) as exc_info:
        raise_api_error(409, "membership_already_exists")

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == {
        "code": "membership_already_exists",
        "message": DEFAULT_API_ERROR_MESSAGES["membership_already_exists"],
    }


def test_raise_api_error_prefers_explicit_message() -> None:
    with pytest.raises(HTTPException) as exc_info:
        raise_api_error(422, "membership_already_exists", "Custom wording")

    assert exc_info.value.detail == {
        "code": "membership_already_exists",
        "message": "Custom wording",
    }


def test_raise_api_error_omits_message_for_unknown_codes_without_override() -> None:
    with pytest.raises(HTTPException) as exc_info:
        raise_api_error(500, "totally_unknown_code")

    assert exc_info.value.detail == {"code": "totally_unknown_code"}
