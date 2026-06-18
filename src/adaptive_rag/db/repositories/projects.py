"""Repository de proyectos."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

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
        embedding_mode: str = "dense",
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
        return self._session.get(Project, project_id)

