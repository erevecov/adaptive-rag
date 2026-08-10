"""Repository de proyectos."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Workspace, WorkspaceMembership


class WorkspaceRepository:
    """Acceso persistente a `Workspace` con transacciones controladas por caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        embedding_mode: str = "dense_sparse",
        retrieval_contextualization_enabled: bool = True,
        budget_config_json: Mapping[str, Any] | None = None,
    ) -> Workspace:
        workspace = Workspace(
            name=name,
            embedding_mode=embedding_mode,
            retrieval_contextualization_enabled=retrieval_contextualization_enabled,
            budget_config_json=(
                dict(budget_config_json) if budget_config_json is not None else None
            ),
        )
        self._session.add(workspace)
        self._session.flush()
        return workspace

    def get(self, workspace_id: UUID) -> Workspace | None:
        workspace = self._session.get(Workspace, workspace_id)
        if workspace is None or workspace.deleted_at is not None:
            return None
        return workspace

    def list(
        self,
        *,
        include_deleted: bool = False,
        member_user_id: UUID | None = None,
    ) -> list[Workspace]:
        statement = select(Workspace)
        if not include_deleted:
            statement = statement.where(Workspace.deleted_at.is_(None))
        if member_user_id is not None:
            statement = statement.join(
                WorkspaceMembership,
                WorkspaceMembership.workspace_id == Workspace.id,
            ).where(WorkspaceMembership.user_id == member_user_id)
        statement = statement.order_by(
            Workspace.created_at,
            Workspace.name,
            Workspace.id,
        )
        return list(self._session.scalars(statement))

    def update(
        self,
        workspace_id: UUID,
        *,
        name: str | None = None,
        embedding_mode: str | None = None,
        retrieval_contextualization_enabled: bool | None = None,
        budget_config_json: Mapping[str, Any] | None = None,
    ) -> Workspace | None:
        workspace = self.get(workspace_id)
        if workspace is None:
            return None
        if name is not None:
            workspace.name = name
        if embedding_mode is not None:
            workspace.embedding_mode = embedding_mode
        if retrieval_contextualization_enabled is not None:
            workspace.retrieval_contextualization_enabled = (
                retrieval_contextualization_enabled
            )
        if budget_config_json is not None:
            workspace.budget_config_json = dict(budget_config_json)
        self._session.flush()
        return workspace

    def soft_delete(self, workspace_id: UUID) -> Workspace | None:
        workspace = self.get(workspace_id)
        if workspace is None:
            return None
        workspace.deleted_at = datetime.now(UTC)
        self._session.flush()
        return workspace
