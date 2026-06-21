# Adaptive RAG Frontend

Frontend scaffold for the M15 chat and history UI.

## Stack

- React
- TypeScript
- Vite
- pnpm

## Local Commands

```text
pnpm install
pnpm dev
pnpm lint
pnpm test
pnpm build
```

## Environment

Create a local `.env.local` when the API client slice needs a backend URL:

```text
VITE_ADAPTIVE_RAG_API_BASE_URL=http://localhost:8000
```

Only public frontend variables belong here. Provider API keys and backend
credentials must stay out of the browser.

## Scope

This scaffold does not call the backend yet. The next M15 slices add the typed
API client, the chat workspace, and the read-only history UI.
