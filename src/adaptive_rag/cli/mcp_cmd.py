"""CLI entry for MCP stdio server."""

from __future__ import annotations

import typer

app = typer.Typer(no_args_is_help=True)


@app.command("serve")
def serve() -> None:
    """Run Adaptive RAG MCP server over stdio (Claude Code / Cursor)."""

    from adaptive_rag.mcp_server import main

    main()
