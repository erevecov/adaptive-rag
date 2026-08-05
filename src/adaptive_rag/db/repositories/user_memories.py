"""Repository for durable user memory items."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models.user_memory import UserMemory


class UserMemoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        user_id: UUID,
        content: str,
        project_id: UUID | None = None,
        status: str = "proposed",
    ) -> UserMemory:
        memory = UserMemory(
            user_id=user_id,
            project_id=project_id,
            content=content,
            status=status,
        )
        self._session.add(memory)
        self._session.flush()
        return memory

    def get(self, *, memory_id: UUID, user_id: UUID | None = None) -> UserMemory | None:
        statement = select(UserMemory).where(UserMemory.id == memory_id)
        if user_id is not None:
            statement = statement.where(UserMemory.user_id == user_id)
        return self._session.scalars(statement).one_or_none()

    def list_for_user(
        self,
        *,
        user_id: UUID,
        project_id: UUID | None = None,
        status: str | None = None,
        include_global: bool = True,
    ) -> list[UserMemory]:
        statement = select(UserMemory).where(UserMemory.user_id == user_id)
        if project_id is not None:
            if include_global:
                statement = statement.where(
                    (UserMemory.project_id == project_id)
                    | (UserMemory.project_id.is_(None))
                )
            else:
                statement = statement.where(UserMemory.project_id == project_id)
        if status is not None:
            statement = statement.where(UserMemory.status == status)
        statement = statement.order_by(UserMemory.created_at.desc(), UserMemory.id)
        return list(self._session.scalars(statement))

    def set_status(
        self,
        *,
        memory_id: UUID,
        status: str,
        reviewed_by_user_id: UUID,
    ) -> UserMemory | None:
        memory = self.get(memory_id=memory_id)
        if memory is None:
            return None
        memory.status = status
        memory.reviewed_at = datetime.now(UTC)
        memory.reviewed_by_user_id = reviewed_by_user_id
        self._session.flush()
        return memory

    def update_content(
        self,
        *,
        memory_id: UUID,
        content: str,
    ) -> UserMemory | None:
        memory = self.get(memory_id=memory_id)
        if memory is None:
            return None
        memory.content = content
        self._session.flush()
        return memory
