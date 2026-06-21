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

The workspace screen can call the chat API, render answer details, and refresh a
small recent-sessions summary. The next M15 slice expands the read-only history
panel with session selection and detail views.
