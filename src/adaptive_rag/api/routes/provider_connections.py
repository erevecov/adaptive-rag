"""HTTP routes for global runtime provider connections."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from adaptive_rag.api.dependencies import (
    get_provider_model_lister,
    get_provider_secret_store,
    get_session,
    get_superadmin_user,
)
from adaptive_rag.api.schemas.provider_connections import (
    ProviderConnectionCheckResponse,
    ProviderConnectionListResponse,
    ProviderConnectionResponse,
    ProviderConnectionUpsertRequestBody,
    ProviderModelListResponse,
    ProviderModelResponse,
    ProviderModelSyncResponse,
    ProviderSecretStatusResponse,
    ProviderSecretUpsertRequestBody,
    SystemTaskListResponse,
    SystemTaskRunResponse,
    SystemTaskStatusResponse,
)
from adaptive_rag.db.models import ProviderConnection, ProviderSecret
from adaptive_rag.db.repositories import (
    ProviderConnectionRepository,
    ProviderModelCatalogRepository,
)
from adaptive_rag.provider_models import ProviderModelInfo, ProviderModelLister
from adaptive_rag.provider_pricing import QWEN_PROVIDER, sync_provider_model_pricing
from adaptive_rag.provider_secrets import (
    ProviderSecretDecryptError,
    ProviderSecretKeyError,
    ProviderSecretStore,
)
from adaptive_rag.runtime.qwen_defaults import (
    ensure_qwen_declared_capability_models,
    materialize_qwen_runtime_defaults,
)
from adaptive_rag.system_scheduler import (
    default_worker_id,
    ensure_registered_tasks,
    run_provider_pricing_system_task,
    system_task_status_payload,
)

router = APIRouter(
    prefix="/runtime-settings",
    tags=["runtime-settings"],
    dependencies=[Depends(get_superadmin_user)],
)


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


@router.post("/connections", response_model=ProviderConnectionResponse)
def create_provider_connection(
    body: ProviderConnectionUpsertRequestBody,
    session: Annotated[Session, Depends(get_session)],
) -> ProviderConnectionResponse:
    repository = ProviderConnectionRepository(session)
    try:
        connection = repository.create_connection(
            provider=body.provider,
            connection_type=body.connection_type,
            base_url=body.base_url,
            capabilities=body.capabilities,
            metadata=body.metadata,
        )
        _upsert_inline_api_key(
            repository=repository,
            connection_id=connection.connection_id,
            api_key=body.api_key,
        )
    except (ProviderSecretKeyError, ValueError) as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProviderConnectionResponse.from_connection(
        connection,
        secrets=repository.list_secret_statuses(connection.connection_id),
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
        _upsert_inline_api_key(
            repository=repository,
            connection_id=connection.connection_id,
            api_key=body.api_key,
        )
    except (ProviderSecretKeyError, ValueError) as exc:
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


@router.get("/system-tasks", response_model=SystemTaskListResponse)
def list_system_tasks(
    session: Annotated[Session, Depends(get_session)],
) -> SystemTaskListResponse:
    """List global in-app system tasks (last run / lease). Superadmin only."""

    rows = ensure_registered_tasks(session)
    session.commit()
    return SystemTaskListResponse(
        items=[
            SystemTaskStatusResponse.model_validate(system_task_status_payload(row))
            for row in rows
        ]
    )


@router.post(
    "/system-tasks/provider-model-pricing/run",
    response_model=SystemTaskRunResponse,
)
def run_provider_model_pricing_task(
    session: Annotated[Session, Depends(get_session)],
    force: bool = True,
) -> SystemTaskRunResponse:
    """Manually run daily Alibaba/Qwen catalog pricing sync. Superadmin only.

    The Compose/prod ``scheduler`` service runs this on the daily interval;
    this endpoint is for smoke and admin re-sync.
    """

    result = run_provider_pricing_system_task(
        session,
        worker_id=default_worker_id(prefix="api-pricing"),
        force=force,
        dry_run=False,
    )
    session.commit()
    return SystemTaskRunResponse(
        task_id=result.task_id,
        status=result.status,
        worker_id=result.worker_id,
        force=result.force,
        report=result.report,
        error=result.error,
    )


@router.get("/models", response_model=ProviderModelListResponse)
def list_provider_models(
    session: Annotated[Session, Depends(get_session)],
    connection_id: str | None = None,
    capability: str | None = None,
) -> ProviderModelListResponse:
    try:
        models = ProviderModelCatalogRepository(session).list_models(
            connection_id=connection_id,
            capability=capability,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    return ProviderModelListResponse(
        items=[ProviderModelResponse.from_model(model) for model in models]
    )


@router.post(
    "/connections/{connection_id}/models/sync",
    response_model=ProviderModelSyncResponse,
)
def sync_provider_models(
    connection_id: str,
    session: Annotated[Session, Depends(get_session)],
    lister: Annotated[ProviderModelLister, Depends(get_provider_model_lister)],
    secret_store: Annotated[ProviderSecretStore, Depends(get_provider_secret_store)],
) -> ProviderModelSyncResponse:
    connection = session.get(ProviderConnection, connection_id)
    if connection is None:
        raise _http_error(ValueError("connection not found"))
    catalog = ProviderModelCatalogRepository(session)
    discovered: list[ProviderModelInfo] = []
    try:
        api_key = _api_key_for_sync(connection, session, secret_store)
        try:
            discovered = lister.list_models(connection, api_key=api_key)
        except ValueError as list_error:
            # Native DashScope service base URLs (rerank/embeddings) often have
            # no OpenAI-compatible /models listing. For Qwen we still seed
            # declared capability models (qwen3-rerank, text-embedding-v4).
            if connection.provider != QWEN_PROVIDER:
                raise
            list_message = str(list_error)
            if not (
                list_message.startswith("provider model")
                or "missing data" in list_message
            ):
                raise
        for model in discovered:
            catalog.upsert_model(
                connection_id=connection.connection_id,
                model_id=model.model_id,
                capabilities=_catalog_capabilities(connection, model),
                metadata=model.metadata,
                pricing=model.pricing,
            )
        if connection.provider == QWEN_PROVIDER:
            # Seed qwen3-rerank / text-embedding-v4 when declared on the
            # connection but missing from OpenAI-compatible /models listings.
            ensure_qwen_declared_capability_models(session, connection)
            materialize_qwen_runtime_defaults(session)
            # Provider /models rarely returns list prices; fill pricing_json from
            # the published Alibaba catalog so Model Catalog UI is not empty.
            sync_provider_model_pricing(session, provider=QWEN_PROVIDER, dry_run=False)
        models = catalog.list_models(connection_id=connection.connection_id)
    except (ProviderSecretDecryptError, ProviderSecretKeyError, ValueError) as exc:
        raise _http_error(exc) from exc
    session.commit()
    return ProviderModelSyncResponse(
        connection_id=connection.connection_id,
        synced_count=len(discovered),
        items=[ProviderModelResponse.from_model(model) for model in models],
    )


@router.post(
    "/connections/{connection_id}/check",
    response_model=ProviderConnectionCheckResponse,
)
def check_provider_connection(
    connection_id: str,
    session: Annotated[Session, Depends(get_session)],
    lister: Annotated[ProviderModelLister, Depends(get_provider_model_lister)],
    secret_store: Annotated[ProviderSecretStore, Depends(get_provider_secret_store)],
) -> ProviderConnectionCheckResponse:
    connection = session.get(ProviderConnection, connection_id)
    if connection is None:
        raise _http_error(ValueError("connection not found"))
    try:
        api_key = _api_key_for_sync(connection, session, secret_store)
        discovered = lister.list_models(connection, api_key=api_key)
    except (ProviderSecretDecryptError, ProviderSecretKeyError) as exc:
        raise _http_error(exc) from exc
    except ValueError as exc:
        return ProviderConnectionCheckResponse(
            connection_id=connection.connection_id,
            ok=False,
            model_count=0,
            message=str(exc),
        )

    return ProviderConnectionCheckResponse(
        connection_id=connection.connection_id,
        ok=True,
        model_count=len(discovered),
        message="provider model list succeeded",
    )


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


def _api_key_for_sync(
    connection: ProviderConnection,
    session: Session,
    secret_store: ProviderSecretStore,
) -> str | None:
    secret = session.get(ProviderSecret, (connection.connection_id, "api_key"))
    if secret is None:
        return None
    return secret_store.decrypt(secret.encrypted_value)


def _upsert_inline_api_key(
    *,
    repository: ProviderConnectionRepository,
    connection_id: str,
    api_key: str | None,
) -> None:
    if api_key is None:
        return
    secret_store = ProviderSecretStore.from_settings()
    repository.upsert_secret(
        connection_id=connection_id,
        secret_name="api_key",  # nosec B106
        secret_value=api_key,
        secret_store=secret_store,
    )


def _catalog_capabilities(
    connection: ProviderConnection,
    model: ProviderModelInfo,
) -> list[str]:
    """Intersect model capabilities with the connection's declared slots.

    When the provider listing omits capabilities (common for OpenAI-compatible
    ``/models``), infer them for Qwen/Model Studio ids so Global Defaults can
    offer chat/embedding/rerank options after sync.
    """

    capabilities = list(model.capabilities)
    if not capabilities and connection.provider == "qwen":
        from adaptive_rag.runtime.qwen_defaults import infer_qwen_model_capabilities

        capabilities = list(infer_qwen_model_capabilities(model.model_id))
    if not capabilities:
        return []
    connection_capabilities = set(connection.capabilities_json)
    return [
        capability
        for capability in capabilities
        if capability in connection_capabilities
    ]


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
    elif message.startswith("provider model"):
        code = "provider_model_sync_failed"
    elif message.startswith("unsupported provider model listing:"):
        code = "provider_model_sync_failed"
    elif message == "provider secret could not be decrypted":
        code = "provider_secret_decrypt_failed"
    elif message.startswith("ADAPTIVE_RAG_PROVIDER_SECRETS_KEY"):
        code = "provider_secret_key_invalid"
    elif message == "connection_not_found":
        return HTTPException(
            status_code=404,
            detail={"code": "connection_not_found", "message": message},
        )
    elif message.startswith("unsupported provider capability:"):
        code = "unsupported_provider_capability"
    else:
        code = "invalid_provider_connection"
    return HTTPException(status_code=422, detail={"code": code, "message": message})
