"""Comandos CLI para authoring de projects."""

from __future__ import annotations

import json
from typing import Annotated, NoReturn
from uuid import UUID

import typer

from adaptive_rag.authoring import (
    AuthoringError,
    project_payload,
)
from adaptive_rag.authoring import (
    create_project as create_authoring_project,
)
from adaptive_rag.authoring import (
    get_project as get_authoring_project,
)
from adaptive_rag.authoring import (
    list_projects as list_authoring_projects,
)
from adaptive_rag.db.session import session_scope

app = typer.Typer(no_args_is_help=True)


@app.command("create")
def create(
    name: Annotated[str, typer.Option("--name")],
) -> None:
    with session_scope() as session:
        try:
            project = create_authoring_project(session, name=name)
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        session.commit()
        payload = project_payload(project)

    typer.echo(json.dumps(payload))


@app.command("list")
def list_projects() -> None:
    with session_scope() as session:
        projects = list_authoring_projects(session)
        payload = {"items": [project_payload(project) for project in projects]}

    typer.echo(json.dumps(payload))


@app.command("show")
def show(
    project_id: Annotated[UUID, typer.Option("--project-id")],
) -> None:
    with session_scope() as session:
        try:
            project = get_authoring_project(session, project_id)
        except AuthoringError as exc:
            _exit_authoring_error(exc)
        payload = project_payload(project)

    typer.echo(json.dumps(payload))


def _exit_authoring_error(error: AuthoringError) -> NoReturn:
    typer.echo(error.detail, err=True)
    raise typer.Exit(1)
