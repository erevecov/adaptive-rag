"""Schemas HTTP para chat attachments."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from adaptive_rag.db.models import ChatAttachment


class ChatAttachmentUploadResponse(BaseModel):
    id: UUID
    kind: str
    filename: str
    mime: str
    size_bytes: int

    @classmethod
    def from_attachment(
        cls,
        attachment: ChatAttachment,
    ) -> ChatAttachmentUploadResponse:
        return cls(
            id=attachment.id,
            kind=attachment.kind,
            filename=attachment.filename,
            mime=attachment.mime,
            size_bytes=attachment.size_bytes,
        )
