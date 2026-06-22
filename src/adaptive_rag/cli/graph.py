"""Comandos CLI para operaciones graph opt-in."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import urlsplit

import typer

from adaptive_rag.cli.dependencies import get_cli_graph_store
from adaptive_rag.config.settings import get_settings
from adaptive_rag.graph import GraphStoreConfigurationError, GraphStoreError

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
