"""HTTP routes for global runtime provider connections."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import get_provider_secret_store, get_session
from adaptive_rag.api.schemas.provider_connections import (
    ProviderConnectionListResponse,
    ProviderConnectionResponse,
    ProviderConnectionUpsertRequestBody,
    ProviderSecretStatusResponse,
    ProviderSecretUpsertRequestBody,
)
from adaptive_rag.db.repositories import ProviderConnectionRepository
from adaptive_rag.provider_secrets import ProviderSecretStore

router = APIRouter(prefix="/runtime-settings", tags=["runtime-settings"])


@router.get("/connections", response_model=ProviderConnectionListResponse)
def list_provider_connections(
    session: Annotated[Session, Depends(get_session)],
) -> ProviderConnectionListResponse:
    repository = ProviderConnectionRepository(session)
    connections = repository.list_connections()
    return ProviderConnectionListResponse(
        items=[
            ProviderConnectionResponse.from_connection(
                connection,
                secrets=repository.list_secret_statuses(connection.connection_id),
            )
            for connection in connections
        ]
    )


@router.put("/connections/{connection_id}", response_model=ProviderConnectionResponse)
def upsert_provider_connection(
    connection_id: str,
    body: ProviderConnectionUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProviderConnectionResponse:
    repository = ProviderConnectionRepository(session)
    try:
        connection = repository.upsert_connection(
            connection_id=connection_id,
            provider=body.provider,
            connection_type=body.connection_type,
            base_url=body.base_url,
            capabilities=body.capabilities,
            metadata=body.metadata,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProviderConnectionResponse.from_connection(
        connection,
        secrets=repository.list_secret_statuses(connection.connection_id),
    )


@router.delete("/connections/{connection_id}")
def delete_provider_connection(
    connection_id: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, bool]:
    deleted = ProviderConnectionRepository(session).delete_connection(connection_id)
    session.commit()
    return {"deleted": deleted}


@router.put(
    "/connections/{connection_id}/secrets/{secret_name}",
    response_model=ProviderSecretStatusResponse,
)
def upsert_provider_secret(
    connection_id: str,
    secret_name: str,
    body: ProviderSecretUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
    secret_store: Annotated[
        ProviderSecretStore,
        Depends(get_provider_secret_store),
    ],
) -> ProviderSecretStatusResponse:
    try:
        status = ProviderConnectionRepository(session).upsert_secret(
            connection_id=connection_id,
            secret_name=secret_name,
            secret_value=body.value,
            secret_store=secret_store,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProviderSecretStatusResponse.from_status(status)


@router.delete("/connections/{connection_id}/secrets/{secret_name}")
def delete_provider_secret(
    connection_id: str,
    secret_name: str,
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, bool]:
    try:
        deleted = ProviderConnectionRepository(session).delete_secret(
            connection_id=connection_id,
            secret_name=secret_name,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    session.commit()
    return {"deleted": deleted}


def _http_error(error: ValueError) -> HTTPException:
    message = str(error)
    if message == "connection not found":
        return HTTPException(
            status_code=404,
            detail={"code": "connection_not_found", "message": message},
        )
    if message.startswith("unsupported provider:"):
        code = "unsupported_provider"
    elif message.startswith("unsupported connection_type:"):
        code = "unsupported_connection_type"
    elif message.startswith("unsupported provider capability:"):
        code = "unsupported_provider_capability"
    elif message.startswith("unsupported secret_name:"):
        code = "unsupported_provider_secret"
    else:
        code = "invalid_provider_connection"
    return HTTPException(status_code=422, detail={"code": code, "message": message})
