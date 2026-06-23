"""Comandos CLI para authoring de sources."""

from __future__ import annotations

import json
from typing import Annotated, Any, NoReturn
from uuid import UUID

import typer

from adaptive_rag.authoring import (
    AuthoringError,
    source_payload,
)
from adaptive_rag.authoring import (
    create_source as create_authoring_source,
)
from adaptive_rag.authoring import (
    get_source as get_authoring_source,
)
from adaptive_rag.authoring import (
    list_sources as list_authoring_sources,
)
from adaptive_rag.db.repositories import SourceFilters
from adaptive_rag.db.session import session_scope

app = typer.Typer(no_args_is_help=True)


@app.command("create")
def create(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    source_type: Annotated[str, typer.Option("--source-type")],
    external_id: Annotated[str, typer.Option("--external-id")],
    content: Annotated[str | None, typer.Option("--content")] = None,
    tag: Annotated[list[str] | None, typer.Option("--tag")] = None,
) -> None:
    extra_metadata = _extra_metadata_from_content(content)

    with session_scope() as session:
        try:
            source = create_authoring_source(
                session,
                project_id=project_id,
                source_type=source_type,
                external_id=external_id,
                tags=tag,
                extra_metadata=extra_metadata,
            )
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        session.commit()
        payload = source_payload(source)

    typer.echo(json.dumps(payload))


@app.command("list")
def list_sources(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    source_type: Annotated[str | None, typer.Option("--source-type")] = None,
    external_id: Annotated[str | None, typer.Option("--external-id")] = None,
    tag: Annotated[str | None, typer.Option("--tag")] = None,
) -> None:
    with session_scope() as session:
        try:
            sources = list_authoring_sources(
                session,
                project_id=project_id,
                filters=SourceFilters(
                    source_type=source_type,
                    external_id=external_id,
                    tag=tag,
                ),
            )
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        payload = {"items": [source_payload(source) for source in sources]}

    typer.echo(json.dumps(payload))


@app.command("show")
def show(
    project_id: Annotated[UUID, typer.Option("--project-id")],
    source_id: Annotated[UUID, typer.Option("--source-id")],
) -> None:
    with session_scope() as session:
        try:
            source = get_authoring_source(
                session,
                project_id=project_id,
                source_id=source_id,
            )
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        payload = source_payload(source)

    typer.echo(json.dumps(payload))


def _extra_metadata_from_content(content: str | None) -> dict[str, Any] | None:
    if content is None:
        return None
    return {"content": content}


def _exit_authoring_error(error: AuthoringError) -> NoReturn:
    typer.echo(error.detail, err=True)
    raise typer.Exit(1)
