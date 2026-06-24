"""Comandos CLI de chat/tool calling."""

from __future__ import annotations

import json
from collections.abc import Callable
from inspect import signature
from typing import Annotated, Any, cast
from uuid import UUID

import typer
from sqlalchemy.orm import Session

from adaptive_rag.api.schemas.chat import (
    ChatObservabilitySummaryResponse,
    ChatSessionDetailResponse,
    ChatSessionListResponse,
)
from adaptive_rag.chat import (
    ChatRequest,
    ChatRunner,
    ChatService,
    ChatServiceError,
    SqlAlchemyChatAuditWriter,
)
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
)
from adaptive_rag.cli.filters import build_retrieval_metadata_filter, parse_cli_datetime
from adaptive_rag.db.repositories import (
    ChatAuditRepository,
    ChatObservabilityRepository,
    ProviderUsageRepository,
)
from adaptive_rag.db.session import session_scope
from adaptive_rag.embeddings import DenseEmbeddingProvider
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.retrieval import RetrievalService

app = typer.Typer(no_args_is_help=True)
sessions_app = typer.Typer(no_args_is_help=True)
observability_app = typer.Typer(no_args_is_help=True)
app.add_typer(sessions_app, name="sessions")
app.add_typer(observability_app, name="observability")


@app.command("ask")
def ask(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    message: Annotated[str, typer.Option("--message")],
    retrieval_limit: Annotated[int, typer.Option("--retrieval-limit")] = 5,
    source_id: Annotated[UUID | None, typer.Option("--source-id")] = None,
    document_id: Annotated[UUID | None, typer.Option("--document-id")] = None,
    source_type: Annotated[str | None, typer.Option("--source-type")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
    source_created_at_from: Annotated[
        str | None,
        typer.Option("--source-created-at-from"),
    ] = None,
    source_created_at_to: Annotated[
        str | None,
        typer.Option("--source-created-at-to"),
    ] = None,
    document_created_at_from: Annotated[
        str | None,
        typer.Option("--document-created-at-from"),
    ] = None,
    document_created_at_to: Annotated[
        str | None,
        typer.Option("--document-created-at-to"),
    ] = None,
) -> None:
    metadata_filter = build_retrieval_metadata_filter(
        source_id=source_id,
        document_id=document_id,
        source_type=source_type,
        tag=tag,
        source_created_at_from=source_created_at_from,
        source_created_at_to=source_created_at_to,
        document_created_at_from=document_created_at_from,
        document_created_at_to=document_created_at_to,
    )
    request = ChatRequest(
        project_id=project_id,
        message=message,
        retrieval_limit=retrieval_limit,
        metadata_filter=metadata_filter,
    )

    with session_scope() as session:
        usage_tracker = InMemoryProviderUsageTracker()
        audit_writer = SqlAlchemyChatAuditWriter(
            session=session,
            chat_audit_repository=ChatAuditRepository(session),
            provider_usage_repository=ProviderUsageRepository(session),
        )
        retrieval_service = RetrievalService(
            session,
            provider=_get_chat_dense_embedding_provider(
                project_id=project_id,
                session=session,
                usage_tracker=usage_tracker,
            ),
        )
        service = ChatService(
            runner=_get_chat_runner(
                project_id=project_id,
                session=session,
                usage_tracker=usage_tracker,
            ),
            retrieval_service=retrieval_service,
            audit_writer=audit_writer,
            provider_usage_records=lambda: usage_tracker.records,
        )
        try:
            response = service.respond(request)
            session.commit()
        except ChatServiceError as exc:
            _commit_or_rollback_chat_error(session)
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc
        except Exception:
            _commit_or_rollback_chat_error(session)
            raise

    typer.echo(json.dumps(serialize_chat_response(response)))


@sessions_app.command("list")
def list_sessions(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    status: Annotated[str | None, typer.Option("--status")] = None,
    limit: Annotated[int, typer.Option("--limit")] = 20,
    cursor: Annotated[str | None, typer.Option("--cursor")] = None,
) -> None:
    with session_scope() as session:
        try:
            page = ChatAuditRepository(session).list_session_summaries(
                project_id=project_id,
                status=status,
                limit=limit,
                cursor=cursor,
            )
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    response = ChatSessionListResponse.from_summary_page(page)
    typer.echo(json.dumps(response.model_dump(mode="json", by_alias=True)))


@sessions_app.command("show")
def show_session(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    session_id: Annotated[UUID, typer.Option("--session-id")],
) -> None:
    with session_scope() as session:
        detail = ChatAuditRepository(session).get_session_detail(
            project_id=project_id,
            session_id=session_id,
        )
        if detail is None:
            typer.echo("chat session not found", err=True)
            raise typer.Exit(1)

    response = ChatSessionDetailResponse.from_detail(detail)
    typer.echo(json.dumps(response.model_dump(mode="json", by_alias=True)))


@observability_app.command("summary")
def observability_summary(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    created_at_from: Annotated[
        str | None,
        typer.Option("--created-at-from"),
    ] = None,
    created_at_to: Annotated[
        str | None,
        typer.Option("--created-at-to"),
    ] = None,
    status: Annotated[str | None, typer.Option("--status")] = None,
) -> None:
    with session_scope() as session:
        try:
            summary = ChatObservabilityRepository(session).get_summary(
                project_id=project_id,
                created_at_from=parse_cli_datetime(
                    created_at_from,
                    field_name="created_at_from",
                ),
                created_at_to=parse_cli_datetime(
                    created_at_to,
                    field_name="created_at_to",
                ),
                status=status,
            )
        except ValueError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(1) from exc

    response = ChatObservabilitySummaryResponse.from_summary(summary)
    typer.echo(json.dumps(response.model_dump(mode="json", by_alias=True)))


def _commit_or_rollback_chat_error(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()


def _get_chat_dense_embedding_provider(
    *,
    project_id: UUID,
    session: Session,
    usage_tracker: InMemoryProviderUsageTracker,
) -> DenseEmbeddingProvider:
    kwargs = _runtime_factory_kwargs(
        get_cli_dense_embedding_provider,
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )
    return cast(
        DenseEmbeddingProvider,
        cast(Any, get_cli_dense_embedding_provider)(**kwargs),
    )


def _get_chat_runner(
    *,
    project_id: UUID,
    session: Session,
    usage_tracker: InMemoryProviderUsageTracker,
) -> ChatRunner:
    kwargs = _runtime_factory_kwargs(
        get_cli_chat_runner,
        project_id=project_id,
        session=session,
        usage_tracker=usage_tracker,
    )
    return cast(ChatRunner, cast(Any, get_cli_chat_runner)(**kwargs))


def _runtime_factory_kwargs(
    factory: Callable[..., object],
    *,
    project_id: UUID,
    session: Session,
    usage_tracker: InMemoryProviderUsageTracker,
) -> dict[str, object]:
    parameters = signature(factory).parameters
    kwargs: dict[str, object] = {}
    if "project_id" in parameters:
        kwargs["project_id"] = project_id
    if "session" in parameters:
        kwargs["session"] = session
    if "usage_tracker" in parameters:
        kwargs["usage_tracker"] = usage_tracker
    return kwargs
