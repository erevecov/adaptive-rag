# Adaptive RAG Frontend

React frontend for authenticated chat, workspace knowledge, operations, and
role-scoped administration.

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

Create a local `.env.local` when the API client needs a backend URL:

```text
VITE_ADAPTIVE_RAG_API_BASE_URL=http://localhost:8000
```

Only public frontend variables belong here. Provider API keys and backend
credentials must stay out of the browser. Human authentication uses the
backend's HttpOnly session cookie; there is no Vite bearer-token variable.

## Scope

The application includes login and mandatory password change, chat/history,
workspace authoring and runtime tools, global user management for superadmins,
and workspace membership management for workspace admins. Browser-side secrets
remain out of scope.
