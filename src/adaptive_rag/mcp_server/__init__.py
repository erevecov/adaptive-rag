"""Minimal MCP stdio server for Adaptive RAG (M49)."""

from adaptive_rag.mcp_server.server import build_server, main, tool_names

__all__ = ["build_server", "main", "tool_names"]
