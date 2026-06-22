"""Comandos CLI para operaciones graph opt-in."""

from __future__ import annotations

import json
from typing import Annotated, Any
from urllib.parse import urlsplit
from uuid import UUID

import typer

from adaptive_rag.cli.dependencies import get_cli_graph_store
from adaptive_rag.config.settings import get_settings
from adaptive_rag.db.session import session_scope
from adaptive_rag.graph import (
    GraphBackfillOperationName,
    GraphBackfillOperationReport,
    GraphStoreConfigurationError,
    GraphStoreError,
    run_graph_backfill_operation,
)

app = typer.Typer(no_args_is_help=True)


@app.command("neo4j-smoke")
def neo4j_smoke() -> None:
    """Valida conectividad Neo4j live usando settings opt-in."""

    store: Any | None = None
    try:
        store = get_cli_graph_store()
        if store.backend != "neo4j":
            raise GraphStoreConfigurationError(
                "ADAPTIVE_RAG_GRAPH_STORE=neo4j is required for neo4j smoke"
            )
        health = store.health_check()
    except GraphStoreError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        _close_store(store)

    settings = get_settings()
    typer.echo(
        json.dumps(
            {
                "backend": health.backend,
                "available": health.available,
                "status": health.status,
                "error_code": health.error_code,
                "uri_scheme": _uri_scheme(settings.neo4j_uri),
                "uri_kind": _uri_kind(settings.neo4j_uri),
            }
        )
    )
    if not health.available:
        raise typer.Exit(1)


@app.command("backfill")
def backfill(
    project_id: Annotated[UUID, typer.Argument(help="Project UUID to backfill.")],
    source_watermark: Annotated[
        str,
        typer.Option(
            "--source-watermark",
            help="Source data watermark recorded on the graph projection.",
        ),
    ],
) -> None:
    """Reconstruye la proyeccion graph de un proyecto."""

    _run_backfill_command(
        project_id=project_id,
        source_watermark=source_watermark,
        operation="backfill",
    )


@app.command("reindex")
def reindex(
    project_id: Annotated[UUID, typer.Argument(help="Project UUID to reindex.")],
    source_watermark: Annotated[
        str,
        typer.Option(
            "--source-watermark",
            help="Source data watermark recorded on the graph projection.",
        ),
    ],
) -> None:
    """Reindexa una proyeccion graph existente para un proyecto."""

    _run_backfill_command(
        project_id=project_id,
        source_watermark=source_watermark,
        operation="reindex",
    )


def _run_backfill_command(
    *,
    project_id: UUID,
    source_watermark: str,
    operation: GraphBackfillOperationName,
) -> None:
    store: Any | None = None
    try:
        store = get_cli_graph_store()
        with session_scope() as session:
            report = run_graph_backfill_operation(
                session=session,
                graph_store=store,
                project_id=project_id,
                source_watermark=source_watermark,
                operation=operation,
            )
    except GraphStoreError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc
    finally:
        _close_store(store)

    typer.echo(json.dumps(_operation_report_payload(report)))
    if report.status != "ready":
        raise typer.Exit(1)


def _operation_report_payload(
    report: GraphBackfillOperationReport,
) -> dict[str, object]:
    return {
        "project_id": str(report.project_id),
        "backend": report.backend,
        "operation": report.operation,
        "previous_status": report.previous_status,
        "status": report.status,
        "source_watermark": report.source_watermark,
        "duration_ms": report.duration_ms,
        "node_count": report.node_count,
        "relationship_count": report.relationship_count,
        "error_code": report.error_code,
    }


def _close_store(store: Any | None) -> None:
    close = getattr(store, "close", None)
    if callable(close):
        close()


def _uri_scheme(uri: str | None) -> str | None:
    if not uri:
        return None
    return urlsplit(uri).scheme or None


def _uri_kind(uri: str | None) -> str:
    scheme = _uri_scheme(uri)
    if scheme == "neo4j+s":
        return "managed_encrypted"
    if scheme in {"neo4j", "bolt", "bolt+s"}:
        return "local_or_self_managed"
    return "unknown"
