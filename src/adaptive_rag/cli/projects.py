"""Comandos CLI para authoring de projects."""

from __future__ import annotations

from typing import Annotated
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
from adaptive_rag.cli.output import echo_json, exit_error
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
            exit_error(exc.detail)
        session.commit()
        payload = project_payload(project)

    echo_json(payload)


@app.command("list")
def list_projects() -> None:
    with session_scope() as session:
        projects = list_authoring_projects(session)
        payload = {"items": [project_payload(project) for project in projects]}

    echo_json(payload)


@app.command("show")
def show(
    project_id: Annotated[UUID, typer.Option("--project-id")],
) -> None:
    with session_scope() as session:
        try:
            project = get_authoring_project(session, project_id)
        except AuthoringError as exc:
            exit_error(exc.detail)
        payload = project_payload(project)

    echo_json(payload)
