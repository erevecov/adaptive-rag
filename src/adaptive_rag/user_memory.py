"""User memory minima: durable propose/approve and chat injection text."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from adaptive_rag.db.models.user_memory import (
    USER_MEMORY_STATUS_VALUES,
    UserMemory,
)
from adaptive_rag.db.repositories.projects import ProjectRepository
from adaptive_rag.db.repositories.user_memories import UserMemoryRepository
from adaptive_rag.db.repositories.users import ProjectMembershipRepository


class UserMemoryError(Exception):
    def __init__(self, detail: str, *, status_code: int) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class UserMemoryView:
    id: UUID
    user_id: UUID
    project_id: UUID | None
    content: str
    status: str


def propose_memory(
    session: Session,
    *,
    user_id: UUID,
    content: str,
    project_id: UUID | None = None,
    is_superadmin: bool = False,
) -> UserMemory:
    text = content.strip()
    if not text:
        raise UserMemoryError("content must not be empty", status_code=422)
    if len(text) > 4000:
        raise UserMemoryError("content exceeds 4000 characters", status_code=422)
    _require_project_scope_access(
        session,
        project_id=project_id,
        user_id=user_id,
        is_superadmin=is_superadmin,
    )
    return UserMemoryRepository(session).create(
        user_id=user_id,
        project_id=project_id,
        content=text,
        status="proposed",
    )


def approve_memory(
    session: Session,
    *,
    memory_id: UUID,
    reviewer_user_id: UUID,
    owner_user_id: UUID | None = None,
    is_superadmin: bool = False,
) -> UserMemory:
    """Approve a proposed memory, or restore a rejected one to injection.

    Rejected → approved covers soft-remove undo without a fourth status.
    """

    return _review(
        session,
        memory_id=memory_id,
        reviewer_user_id=reviewer_user_id,
        owner_user_id=owner_user_id,
        status="approved",
        require_project_access=True,
        is_superadmin=is_superadmin,
        allowed_from_statuses=("proposed", "rejected"),
    )


def reject_memory(
    session: Session,
    *,
    memory_id: UUID,
    reviewer_user_id: UUID,
    owner_user_id: UUID | None = None,
) -> UserMemory:
    """Reject a proposed memory, or soft-remove an approved one from injection.

    Approved → rejected is intentional product behavior: remove injection without
    adding a fourth status. Already-rejected items stay 409.
    """

    return _review(
        session,
        memory_id=memory_id,
        reviewer_user_id=reviewer_user_id,
        owner_user_id=owner_user_id,
        status="rejected",
        require_project_access=False,
        is_superadmin=False,
        allowed_from_statuses=("proposed", "approved"),
    )


def update_proposed_memory(
    session: Session,
    *,
    memory_id: UUID,
    content: str,
    owner_user_id: UUID,
) -> UserMemory:
    """Edit proposed memory content before approve/reject."""

    text = content.strip()
    if not text:
        raise UserMemoryError("content must not be empty", status_code=422)
    if len(text) > 4000:
        raise UserMemoryError("content exceeds 4000 characters", status_code=422)
    repo = UserMemoryRepository(session)
    memory = repo.get(memory_id=memory_id, user_id=owner_user_id)
    if memory is None:
        raise UserMemoryError("memory not found", status_code=404)
    if memory.status != "proposed":
        raise UserMemoryError(
            f"only proposed memories can be edited (status is {memory.status})",
            status_code=409,
        )
    updated = repo.update_content(memory_id=memory_id, content=text)
    if updated is None:
        raise UserMemoryError("memory not found", status_code=404)
    return updated


def list_memories(
    session: Session,
    *,
    user_id: UUID,
    project_id: UUID | None = None,
    status: str | None = None,
) -> list[UserMemory]:
    if status is not None and status not in USER_MEMORY_STATUS_VALUES:
        raise UserMemoryError(
            f"status must be one of {', '.join(USER_MEMORY_STATUS_VALUES)}",
            status_code=422,
        )
    return UserMemoryRepository(session).list_for_user(
        user_id=user_id,
        project_id=project_id,
        status=status,
        include_global=True,
    )


def approved_injection_text(
    session: Session,
    *,
    user_id: UUID,
    project_id: UUID | None = None,
    max_items: int = 8,
) -> str:
    """Return approved memory text for optional chat context injection."""

    memories = UserMemoryRepository(session).list_for_user(
        user_id=user_id,
        project_id=project_id,
        status="approved",
        include_global=True,
    )
    if not memories:
        return ""
    lines = [f"- {item.content.strip()}" for item in memories[:max_items]]
    return "User memory (approved):\n" + "\n".join(lines)


def memory_payload(memory: UserMemory) -> dict[str, Any]:
    return {
        "id": str(memory.id),
        "user_id": str(memory.user_id),
        "project_id": str(memory.project_id) if memory.project_id else None,
        "content": memory.content,
        "status": memory.status,
        "created_at": memory.created_at.isoformat() if memory.created_at else None,
        "reviewed_at": memory.reviewed_at.isoformat() if memory.reviewed_at else None,
        "reviewed_by_user_id": (
            str(memory.reviewed_by_user_id) if memory.reviewed_by_user_id else None
        ),
    }


def memories_payload(items: Sequence[UserMemory]) -> dict[str, Any]:
    return {"items": [memory_payload(item) for item in items]}


def _require_project_scope_access(
    session: Session,
    *,
    project_id: UUID | None,
    user_id: UUID,
    is_superadmin: bool,
) -> None:
    """Require membership (or superadmin) for project-scoped memory."""

    if project_id is None:
        return
    project = ProjectRepository(session).get(project_id)
    if project is None:
        raise UserMemoryError("project not found", status_code=404)
    if is_superadmin:
        return
    membership = ProjectMembershipRepository(session).get_membership(
        project_id=project_id,
        user_id=user_id,
    )
    if membership is None:
        raise UserMemoryError("project access required", status_code=403)


def _review(
    session: Session,
    *,
    memory_id: UUID,
    reviewer_user_id: UUID,
    owner_user_id: UUID | None,
    status: str,
    require_project_access: bool,
    is_superadmin: bool,
    allowed_from_statuses: tuple[str, ...] = ("proposed",),
) -> UserMemory:
    repo = UserMemoryRepository(session)
    memory = repo.get(memory_id=memory_id, user_id=owner_user_id)
    if memory is None:
        raise UserMemoryError("memory not found", status_code=404)
    if memory.status not in allowed_from_statuses:
        raise UserMemoryError(
            f"memory is already {memory.status}",
            status_code=409,
        )
    if require_project_access:
        _require_project_scope_access(
            session,
            project_id=memory.project_id,
            user_id=reviewer_user_id,
            is_superadmin=is_superadmin,
        )
    updated = repo.set_status(
        memory_id=memory_id,
        status=status,
        reviewed_by_user_id=reviewer_user_id,
    )
    if updated is None:
        raise UserMemoryError("memory not found", status_code=404)
    return updated
