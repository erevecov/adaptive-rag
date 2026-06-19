"""Rutas HTTP de retrieval."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from adaptive_rag.api.dependencies import get_retrieval_service
from adaptive_rag.api.schemas.retrieval import (
    RetrievalSearchRequestBody,
    RetrievalSearchResponse,
)
from adaptive_rag.retrieval import RetrievalService, RetrievalServiceError

router = APIRouter(
    prefix="/projects/{project_id}/retrieval",
    tags=["retrieval"],
)


@router.post("/search", response_model=RetrievalSearchResponse)
def search_retrieval(
    project_id: UUID,
    body: RetrievalSearchRequestBody,
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> RetrievalSearchResponse:
    try:
        results = service.search(body.to_service_request(project_id))
    except RetrievalServiceError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    return RetrievalSearchResponse.from_service_results(results)
