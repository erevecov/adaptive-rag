"""Comandos CLI para authoring de workspaces."""

from __future__ import annotations

import json
from typing import Annotated, NoReturn
from uuid import UUID

import typer

from adaptive_rag.authoring import (
    AuthoringError,
    workspace_payload,
)
from adaptive_rag.authoring import (
    create_workspace as create_authoring_workspace,
)
from adaptive_rag.authoring import (
    get_workspace as get_authoring_workspace,
)
from adaptive_rag.authoring import (
    list_workspaces as list_authoring_workspaces,
)
from adaptive_rag.db.session import session_scope

app = typer.Typer(no_args_is_help=True)


@app.command("create")
def create(
    name: Annotated[str, typer.Option("--name")],
) -> None:
    with session_scope() as session:
        try:
            workspace = create_authoring_workspace(session, name=name)
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        session.commit()
        payload = workspace_payload(workspace)

    typer.echo(json.dumps(payload))


@app.command("list")
def list_workspaces() -> None:
    with session_scope() as session:
        workspaces = list_authoring_workspaces(session)
        payload = {"items": [workspace_payload(workspace) for workspace in workspaces]}

    typer.echo(json.dumps(payload))


@app.command("show")
def show(
    workspace_id: Annotated[UUID, typer.Option("--workspace-id")],
) -> None:
    with session_scope() as session:
        try:
            workspace = get_authoring_workspace(session, workspace_id)
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        payload = workspace_payload(workspace)

    typer.echo(json.dumps(payload))


def _exit_authoring_error(error: AuthoringError) -> NoReturn:
    typer.echo(error.detail, err=True)
    raise typer.Exit(1)
