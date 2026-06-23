"""Rutas HTTP de retrieval."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    RerankProviderFactory,
    SparseEmbeddingProviderFactory,
    get_dense_embedding_provider,
    get_graph_retriever,
    get_rerank_provider_factory,
    get_session,
    get_sparse_embedding_provider_factory,
)
from adaptive_rag.api.schemas.retrieval import (
    RetrievalSearchRequestBody,
    RetrievalSearchResponse,
)
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.graph import GraphRetriever
from adaptive_rag.retrieval import RetrievalService, RetrievalServiceError

router = APIRouter(
    prefix="/projects/{project_id}/retrieval",
    tags=["retrieval"],
)


@router.post(
    "/search",
    response_model=RetrievalSearchResponse,
)
def search_retrieval(
    project_id: UUID,
    body: RetrievalSearchRequestBody,
    session: Annotated[Session, Depends(get_session)],
    provider: Annotated[DenseEmbeddingProvider, Depends(get_dense_embedding_provider)],
    rerank_provider_factory: Annotated[
        RerankProviderFactory,
        Depends(get_rerank_provider_factory),
    ],
    sparse_provider_factory: Annotated[
        SparseEmbeddingProviderFactory,
        Depends(get_sparse_embedding_provider_factory),
    ],
    graph_retriever: Annotated[
        GraphRetriever | None,
        Depends(get_graph_retriever),
    ],
) -> RetrievalSearchResponse:
    try:
        body.validate_rerank_options()
        request = body.to_service_request(project_id)
        service = RetrievalService(
            session,
            provider=provider,
            sparse_provider=(
                sparse_provider_factory()
                if request.strategy == "dense_sparse"
                else None
            ),
            reranker=(
                rerank_provider_factory() if request.rerank is not None else None
            ),
            graph_retriever=graph_retriever,
        )
        results = service.search(request)
    except (RetrievalServiceError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    return RetrievalSearchResponse.from_service_results(results)
