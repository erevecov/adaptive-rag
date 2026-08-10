"""Schemas HTTP para authoring publico de workspaces y sources."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from adaptive_rag.db.models import Source, Workspace


class WorkspaceCreateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    embedding_mode: str = "dense_sparse"
    retrieval_contextualization_enabled: bool = True
    budget_config_json: dict[str, Any] | None = None


class WorkspaceUpdateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    embedding_mode: str | None = None
    retrieval_contextualization_enabled: bool | None = None
    budget_config_json: dict[str, Any] | None = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    embedding_mode: str
    retrieval_contextualization_enabled: bool
    budget_config_json: dict[str, Any] | None
    access_role: str | None
    can_access: bool
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_workspace(
        cls,
        workspace: Workspace,
        *,
        access_role: str | None = None,
        can_access: bool = True,
    ) -> WorkspaceResponse:
        return cls(
            id=workspace.id,
            name=workspace.name,
            embedding_mode=workspace.embedding_mode,
            retrieval_contextualization_enabled=(
                workspace.retrieval_contextualization_enabled
            ),
            budget_config_json=workspace.budget_config_json,
            access_role=access_role,
            can_access=can_access,
            created_at=workspace.created_at,
            updated_at=workspace.updated_at,
            deleted_at=workspace.deleted_at,
        )


class WorkspaceListResponse(BaseModel):
    items: list[WorkspaceResponse]

    @classmethod
    def from_workspaces(cls, workspaces: list[Workspace]) -> WorkspaceListResponse:
        return cls(
            items=[
                WorkspaceResponse.from_workspace(workspace) for workspace in workspaces
            ]
        )


class SourceCreateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_type: str
    external_id: str
    tags: list[str] | None = None
    extra_metadata: dict[str, Any] | None = None


class SourceUpdateRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_id: str | None = None
    tags: list[str] | None = None
    extra_metadata: dict[str, Any] | None = None


class SourceResponse(BaseModel):
    id: UUID
    workspace_id: UUID
    source_type: str
    external_id: str
    tags: list[str] | None
    extra_metadata: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @classmethod
    def from_source(cls, source: Source) -> SourceResponse:
        return cls(
            id=source.id,
            workspace_id=source.workspace_id,
            source_type=source.source_type,
            external_id=source.external_id,
            tags=source.tags,
            extra_metadata=source.extra_metadata,
            created_at=source.created_at,
            updated_at=source.updated_at,
            deleted_at=source.deleted_at,
        )


class SourceListResponse(BaseModel):
    items: list[SourceResponse]

    @classmethod
    def from_sources(cls, sources: list[Source]) -> SourceListResponse:
        return cls(items=[SourceResponse.from_source(source) for source in sources])
