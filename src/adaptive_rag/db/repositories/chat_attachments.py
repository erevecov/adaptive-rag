"""Repository for chat attachments uploaded by users."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models.chat_attachment import ChatAttachment


class ChatAttachmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        workspace_id: UUID,
        kind: str,
        mime: str,
        filename: str,
        size_bytes: int,
        content: bytes,
        user_id: UUID | None = None,
        session_id: UUID | None = None,
        extracted_text: str | None = None,
        status: str = "ready",
    ) -> ChatAttachment:
        attachment = ChatAttachment(
            workspace_id=workspace_id,
            user_id=user_id,
            session_id=session_id,
            kind=kind,
            mime=mime,
            filename=filename,
            size_bytes=size_bytes,
            content=content,
            extracted_text=extracted_text,
            status=status,
        )
        self._session.add(attachment)
        self._session.flush()
        return attachment

    def get(self, *, attachment_id: UUID, workspace_id: UUID) -> ChatAttachment | None:
        statement = select(ChatAttachment).where(
            ChatAttachment.id == attachment_id,
            ChatAttachment.workspace_id == workspace_id,
        )
        return self._session.scalars(statement).one_or_none()

    def get_owned(
        self,
        *,
        attachment_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> ChatAttachment | None:
        statement = select(ChatAttachment).where(
            ChatAttachment.id == attachment_id,
            ChatAttachment.workspace_id == workspace_id,
            ChatAttachment.user_id == user_id,
        )
        return self._session.scalars(statement).one_or_none()

    def list_owned_by_ids(
        self,
        *,
        workspace_id: UUID,
        user_id: UUID,
        attachment_ids: Sequence[UUID],
    ) -> list[ChatAttachment]:
        if not attachment_ids:
            return []
        statement = select(ChatAttachment).where(
            ChatAttachment.workspace_id == workspace_id,
            ChatAttachment.user_id == user_id,
            ChatAttachment.id.in_(attachment_ids),
        )
        return list(self._session.scalars(statement))

    def delete(
        self,
        *,
        attachment_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
    ) -> bool:
        attachment = self.get_owned(
            attachment_id=attachment_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        if attachment is None:
            return False
        self._session.delete(attachment)
        self._session.flush()
        return True
