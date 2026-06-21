"""Comandos CLI de chat/tool calling."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

import typer
from sqlalchemy.orm import Session

from adaptive_rag.chat import (
    ChatRequest,
    ChatService,
    ChatServiceError,
    SqlAlchemyChatAuditWriter,
)
from adaptive_rag.chat.payloads import serialize_chat_response
from adaptive_rag.cli.dependencies import (
    get_cli_chat_runner,
    get_cli_dense_embedding_provider,
)
from adaptive_rag.cli.filters import build_retrieval_metadata_filter
from adaptive_rag.db.repositories import ChatAuditRepository, ProviderUsageRepository
from adaptive_rag.db.session import session_scope
from adaptive_rag.provider_usage import InMemoryProviderUsageTracker
from adaptive_rag.retrieval import RetrievalService

app = typer.Typer(no_args_is_help=True)


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
            chat_audit_repository=ChatAuditRepository(session),
            provider_usage_repository=ProviderUsageRepository(session),
        )
        retrieval_service = RetrievalService(
            session,
            provider=get_cli_dense_embedding_provider(),
        )
        service = ChatService(
            runner=get_cli_chat_runner(),
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

    typer.echo(json.dumps(serialize_chat_response(response)))


def _commit_or_rollback_chat_error(session: Session) -> None:
    try:
        session.commit()
    except Exception:
        session.rollback()
