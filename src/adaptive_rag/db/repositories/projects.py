"""Repository de proyectos."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from adaptive_rag.db.models import Project


class ProjectRepository:
    """Acceso persistente a `Project` con transacciones controladas por caller."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        name: str,
        embedding_mode: str = "dense_sparse",
        retrieval_contextualization_enabled: bool = True,
        budget_config_json: Mapping[str, Any] | None = None,
    ) -> Project:
        project = Project(
            name=name,
            embedding_mode=embedding_mode,
            retrieval_contextualization_enabled=retrieval_contextualization_enabled,
            budget_config_json=(
                dict(budget_config_json) if budget_config_json is not None else None
            ),
        )
        self._session.add(project)
        self._session.flush()
        return project

    def get(self, project_id: UUID) -> Project | None:
        project = self._session.get(Project, project_id)
        if project is None or project.deleted_at is not None:
            return None
        return project

    def list(self, *, include_deleted: bool = False) -> list[Project]:
        statement = select(Project)
        if not include_deleted:
            statement = statement.where(Project.deleted_at.is_(None))
        statement = statement.order_by(
            Project.created_at,
            Project.name,
            Project.id,
        )
        return list(self._session.scalars(statement))

    def update(
        self,
        project_id: UUID,
        *,
        name: str | None = None,
        embedding_mode: str | None = None,
        retrieval_contextualization_enabled: bool | None = None,
        budget_config_json: Mapping[str, Any] | None = None,
    ) -> Project | None:
        project = self.get(project_id)
        if project is None:
            return None
        if name is not None:
            project.name = name
        if embedding_mode is not None:
            project.embedding_mode = embedding_mode
        if retrieval_contextualization_enabled is not None:
            project.retrieval_contextualization_enabled = (
                retrieval_contextualization_enabled
            )
        if budget_config_json is not None:
            project.budget_config_json = dict(budget_config_json)
        self._session.flush()
        return project

    def soft_delete(self, project_id: UUID) -> Project | None:
        project = self.get(project_id)
        if project is None:
            return None
        project.deleted_at = datetime.now(UTC)
        self._session.flush()
        return project

