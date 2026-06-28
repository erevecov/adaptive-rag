"""Schemas HTTP para authoring publico de projects y sources."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from adaptive_rag.db.models import Project, Source


class ProjectCreateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    embedding_mode: str = "dense_sparse"
    retrieval_contextualization_enabled: bool = True
    budget_config_json: dict[str, Any] | None = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    embedding_mode: str
    retrieval_contextualization_enabled: bool
    budget_config_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_project(cls, project: Project) -> ProjectResponse:
        return cls(
            id=project.id,
            name=project.name,
            embedding_mode=project.embedding_mode,
            retrieval_contextualization_enabled=(
                project.retrieval_contextualization_enabled
            ),
            budget_config_json=project.budget_config_json,
            created_at=project.created_at,
            updated_at=project.updated_at,
        )


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]

    @classmethod
    def from_projects(cls, projects: list[Project]) -> ProjectListResponse:
        return cls(
            items=[ProjectResponse.from_project(project) for project in projects]
        )


class SourceCreateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str
    external_id: str
    tags: list[str] | None = None
    extra_metadata: dict[str, Any] | None = None


class SourceResponse(BaseModel):
    id: UUID
    project_id: UUID
    source_type: str
    external_id: str
    tags: list[str] | None
    extra_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_source(cls, source: Source) -> SourceResponse:
        return cls(
            id=source.id,
            project_id=source.project_id,
            source_type=source.source_type,
            external_id=source.external_id,
            tags=source.tags,
            extra_metadata=source.extra_metadata,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )


class SourceListResponse(BaseModel):
    items: list[SourceResponse]

    @classmethod
    def from_sources(cls, sources: list[Source]) -> SourceListResponse:
        return cls(items=[SourceResponse.from_source(source) for source in sources])
