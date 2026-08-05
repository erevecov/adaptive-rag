"""HTTP surface for durable user memory (Bloque C minima)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from adaptive_rag import user_memory
from adaptive_rag.api.dependencies import get_current_user, get_session
from adaptive_rag.auth import CurrentPrincipal

router = APIRouter(tags=["user-memory"])


class MemoryProposeBody(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    project_id: UUID | None = None


@router.post("/users/me/memories", status_code=201)
def propose_my_memory(
    body: MemoryProposeBody,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> dict[str, Any]:
    if current.user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        memory = user_memory.propose_memory(
            session,
            user_id=current.user_id,
            content=body.content,
            project_id=body.project_id,
        )
    except user_memory.UserMemoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    session.commit()
    return user_memory.memory_payload(memory)


@router.get("/users/me/memories")
def list_my_memories(
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
    project_id: UUID | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    if current.user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        items = user_memory.list_memories(
            session,
            user_id=current.user_id,
            project_id=project_id,
            status=status,
        )
    except user_memory.UserMemoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return user_memory.memories_payload(items)


@router.post("/users/me/memories/{memory_id}/approve")
def approve_my_memory(
    memory_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> dict[str, Any]:
    if current.user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        memory = user_memory.approve_memory(
            session,
            memory_id=memory_id,
            reviewer_user_id=current.user_id,
            owner_user_id=current.user_id,
        )
    except user_memory.UserMemoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    session.commit()
    return user_memory.memory_payload(memory)


@router.post("/users/me/memories/{memory_id}/reject")
def reject_my_memory(
    memory_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    current: Annotated[CurrentPrincipal, Depends(get_current_user)],
) -> dict[str, Any]:
    if current.user_id is None:
        raise HTTPException(status_code=401, detail="authentication required")
    try:
        memory = user_memory.reject_memory(
            session,
            memory_id=memory_id,
            reviewer_user_id=current.user_id,
            owner_user_id=current.user_id,
        )
    except user_memory.UserMemoryError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    session.commit()
    return user_memory.memory_payload(memory)
