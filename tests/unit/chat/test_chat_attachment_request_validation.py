"""Validate attachment_ids limits map to ChatAttachmentError (not 500)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from adaptive_rag.api.schemas.chat import ChatRequestBody
from adaptive_rag.chat.attachments import (
    MAX_ATTACHMENTS_PER_MESSAGE,
    ChatAttachmentError,
)


def test_to_service_request_rejects_more_than_max_attachments() -> None:
    body = ChatRequestBody(
        message="hello",
        attachment_ids=[uuid4() for _ in range(MAX_ATTACHMENTS_PER_MESSAGE + 1)],
    )
    with pytest.raises(ChatAttachmentError) as exc_info:
        body.to_service_request(uuid4())
    assert exc_info.value.code == "invalid_attachment"
    assert "5" in exc_info.value.message


def test_to_service_request_allows_max_attachments() -> None:
    body = ChatRequestBody(
        message="hello",
        attachment_ids=[uuid4() for _ in range(MAX_ATTACHMENTS_PER_MESSAGE)],
    )
    request = body.to_service_request(uuid4())
    assert len(request.attachments) == MAX_ATTACHMENTS_PER_MESSAGE
