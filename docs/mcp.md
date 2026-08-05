# MCP stdio server (M49)

Local-first MCP tools for Claude Code / Cursor.

## Run

```bash
uv run adaptive-rag mcp serve
```

Uses the same env as the API/CLI (`ADAPTIVE_RAG_*`, database, fake or live
providers).

## Tools

| Tool | Purpose |
|------|---------|
| `list_projects` | List projects |
| `list_sources` | List sources for a project |
| `search` | Retrieval search (`dense_sparse`) |
| `ask` | Grounded chat answer |
| `ingest_text` | Create markdown source + enqueue `ingest_source` |

## Auth

Same local process as CLI — database URL and provider settings from env. No
OAuth/hosted MCP. Write tools limited to source create + enqueue.

## Cursor / Claude Code

```json
{
  "command": "uv",
  "args": ["run", "adaptive-rag", "mcp", "serve"],
  "cwd": "/path/to/adaptive-rag"
}
```
