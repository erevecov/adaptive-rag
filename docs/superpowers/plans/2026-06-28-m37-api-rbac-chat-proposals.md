# M37 API RBAC Chat Proposals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the M37 persistence foundation into API auth, project access control, user-scoped chat history, and chat-sourced knowledge proposal workflows.

**Architecture:** Add a small local bearer-token auth layer backed by `UserAccessToken` hashes. Keep project RBAC in API dependencies/services so existing repositories stay transaction-owned by callers. Preserve bootstrap compatibility by treating an empty `users` table as an unauthenticated bootstrap superadmin for first setup and legacy tests.

**Tech Stack:** Python 3.12+, FastAPI, SQLAlchemy 2, pytest, Pydantic, TypeScript API client.

---

## File Structure

- Create: `src/adaptive_rag/auth.py` for token hashing, current-principal resolution, project role checks, and bootstrap mode.
- Create: `src/adaptive_rag/api/schemas/auth.py` for user, membership, current-user, and knowledge proposal request/response models.
- Create: `src/adaptive_rag/api/routes/auth.py` for `/auth/me`, `/admin/users`, and project membership endpoints.
- Create: `src/adaptive_rag/api/routes/knowledge.py` for chat-sourced knowledge proposal submit/review endpoints.
- Modify: `src/adaptive_rag/api/dependencies.py` to expose `get_current_user` and role dependencies.
- Modify: `src/adaptive_rag/api/app.py` to include auth and knowledge routers.
- Modify: `src/adaptive_rag/api/routes/authoring.py` to enforce superadmin/project RBAC while still listing all project names.
- Modify: `src/adaptive_rag/api/routes/chat.py` to require project access and scope session history/details to the current user.
- Modify: `src/adaptive_rag/api/schemas/authoring.py` and `src/adaptive_rag/api/schemas/chat.py` to expose access metadata and session owner metadata.
- Modify: `src/adaptive_rag/chat/models.py`, `src/adaptive_rag/chat/audit.py`, and `src/adaptive_rag/db/repositories/chat_audit.py` to carry `user_id`.
- Modify: `frontend/src/lib/apiClient.ts` and tests to carry auth headers and new contracts.
- Test: `tests/integration/api/test_auth_rbac.py`
- Test: `tests/integration/api/test_knowledge_proposals.py`
- Modify tests: `tests/integration/api/test_authoring.py`, `tests/integration/api/test_chat.py`, `tests/unit/chat/test_chat_audit_wiring.py`, and `tests/unit/db/repositories/test_chat_audit_repository.py`

## Task 1: Auth API and Project Membership RBAC

- [x] **Step 1: Write failing auth/RBAC API tests**

Create `tests/integration/api/test_auth_rbac.py` with helpers that create `Project`, `User`, `UserAccessToken`, and `ProjectMembership` tables. Cover:

```python
def test_me_resolves_bearer_token_user() -> None:
    response = client.get("/auth/me", headers=bearer_header("viewer-token"))
    assert response.status_code == 200
    assert response.json()["login"] == "viewer@example.com"
```

Also cover: unauthenticated with users present returns 401, bootstrap no-users can create the first superadmin, superadmin creates users, superadmin and project admin can upsert memberships, viewer cannot manage memberships, project list exposes all names with `can_access` false for unassigned users, and project detail returns 403 when a user lacks project access.

- [x] **Step 2: Verify auth/RBAC tests fail**

Run: `uv run pytest tests\integration\api\test_auth_rbac.py -q`

Expected: FAIL with missing `adaptive_rag.auth` or missing routes.

- [x] **Step 3: Implement auth helpers, schemas, routes, and authoring guards**

Add `hash_access_token(raw_token: str) -> str` using `sha256:<hex>`. Add current-user resolution from `Authorization: Bearer <token>`, bootstrap principal when no users exist, project access helpers for `viewer`, `contributor`, `admin`, and `superadmin`. Add `/auth/me`, `/admin/users`, `/projects/{project_id}/memberships` endpoints. Update `GET /projects` to return all projects with `access_role` and `can_access`; update `POST /projects` to require superadmin; update project/source endpoints to enforce access/contributor rules.

- [x] **Step 4: Verify auth/RBAC tests pass**

Run: `uv run pytest tests\integration\api\test_auth_rbac.py tests\integration\api\test_authoring.py -q`

Expected: PASS.

## Task 2: User-Scoped Chat Sessions

- [x] **Step 1: Write failing chat ownership tests**

Extend chat audit repository/unit and integration tests to assert `ChatRequest(user_id=...)` persists `ChatSession.user_id`, a viewer only lists and loads their own sessions, and superadmin can inspect all project sessions.

- [x] **Step 2: Verify chat ownership tests fail**

Run: `uv run pytest tests\unit\db\repositories\test_chat_audit_repository.py tests\integration\api\test_chat.py -q`

Expected: FAIL because `user_id` is not yet carried through chat request/audit/API filtering.

- [x] **Step 3: Implement user_id through chat service and API**

Add `user_id: UUID | None = None` to `ChatRequest` and `ChatRunnerRequest`. Update `ChatAuditRepository.create_session`, `list_session_summaries`, and `get_session_detail` to accept optional `user_id` filtering. Update `SqlAlchemyChatAuditWriter.start_session` to pass `request.user_id`. Update chat route body conversion to include current user id and use user-scoped history for non-superadmins.

- [x] **Step 4: Verify chat ownership tests pass**

Run: `uv run pytest tests\unit\db\repositories\test_chat_audit_repository.py tests\unit\chat tests\integration\api\test_chat.py -q`

Expected: PASS.

## Task 3: Chat-Sourced Knowledge Proposals

- [x] **Step 1: Write failing proposal API tests**

Create `tests/integration/api/test_knowledge_proposals.py` covering viewer submit creates `pending`, contributor submit creates an approved source immediately, contributor/admin can list pending proposals, refine pending proposal, approve pending proposal into a source, reject pending proposal with reason, viewer cannot review, and contributor cannot review a project without membership.

- [x] **Step 2: Verify proposal API tests fail**

Run: `uv run pytest tests\integration\api\test_knowledge_proposals.py -q`

Expected: FAIL with missing route.

- [x] **Step 3: Implement knowledge proposal schemas and route**

Add request/response schemas for proposal submit/refine/approve/reject. Add route prefix `/projects/{project_id}/knowledge-proposals`. Implement submit using project role: `viewer` creates pending proposal; `contributor`, `admin`, and `superadmin` create a `Source` from the submitted/refined text and mark the proposal approved by the submitter. Review endpoints require contributor-or-higher and project scope.

- [x] **Step 4: Verify proposal API tests pass**

Run: `uv run pytest tests\integration\api\test_knowledge_proposals.py -q`

Expected: PASS.

## Task 4: Frontend API Client Contract

- [x] **Step 1: Write failing API client tests**

Extend `frontend/src/lib/apiClient.test.ts` to cover `authToken` Authorization header, `getCurrentUser`, membership upsert/list, knowledge proposal submit/review methods, and project access fields.

- [x] **Step 2: Verify frontend client tests fail**

Run: `pnpm --dir frontend test -- --run src/lib/apiClient.test.ts`

Expected: FAIL with missing client options/methods/types.

- [x] **Step 3: Implement API client auth and methods**

Add optional `authToken` to `createApiClient`, attach `Authorization: Bearer <token>` to JSON and stream requests, add new TypeScript types and methods for auth/memberships/proposals, and preserve existing call sites when no token is configured.

- [x] **Step 4: Verify frontend client tests pass**

Run: `pnpm --dir frontend test -- --run src/lib/apiClient.test.ts`

Expected: PASS.

## Task 5: Validation and Commit

- [x] **Step 1: Run backend validation**

Run:

```powershell
uv run pytest tests\unit\db\repositories tests\unit\chat tests\integration\api -q
uv run ruff check src tests
uv run mypy src\adaptive_rag
```

Expected: PASS.

- [x] **Step 2: Run frontend validation**

Run:

```powershell
pnpm --dir frontend test -- --run
pnpm --dir frontend lint
pnpm --dir frontend build
```

Expected: PASS.

- [x] **Step 3: Run OpenSpec and diff checks**

Run:

```powershell
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
git diff --check
```

Expected: PASS.

- [x] **Step 4: Commit the slice**

Run:

```powershell
git add src tests frontend docs openspec
git commit -m "feat: enforce m37 project rbac flows"
```

Expected: commit succeeds on `codex/m37-project-rbac-chat-knowledge`.

## Self-Review

- Spec coverage: this plan covers role-based project access, all-project name listing, superadmin user/project administration, project admin membership administration, user-owned chat sessions, chat-sourced knowledge proposal submission/review, frontend controls, and final OpenSpec archive.
- Placeholder scan: no `TBD`, `TODO`, `FIXME`, or unspecified command remains.
- Type consistency: route names, schema names, repository names, and role labels match the M37 persistence foundation.
