# M37 Auth Schema Repositories Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the M37 persistence foundation for local users, project memberships, chat session ownership, and chat-sourced knowledge proposals.

**Architecture:** This slice is backend persistence only: SQLAlchemy models, Alembic migration, focused repositories, and exports. API guards, chat-service wiring, frontend project selector, and ingestion bridge are deferred to later M37 slices that consume this foundation.

**Tech Stack:** Python 3.12+, SQLAlchemy 2, Alembic, pytest, ruff, mypy, OpenSpec.

---

## File Structure

- Create: `src/adaptive_rag/db/models/user.py` for `User`, local token hashes, and project membership models.
- Create: `src/adaptive_rag/db/models/knowledge_proposal.py` for pending/approved/rejected chat knowledge proposals.
- Modify: `src/adaptive_rag/db/models/chat_session.py` to add nullable `user_id` in this compatibility slice and an index for user-scoped history.
- Modify: `src/adaptive_rag/db/models/__init__.py` to export new models and value tuples.
- Create: `src/adaptive_rag/db/repositories/users.py` for local users, token hashes, and project memberships.
- Create: `src/adaptive_rag/db/repositories/knowledge_proposals.py` for proposal create/list/refine/approve/reject.
- Modify: `src/adaptive_rag/db/repositories/__init__.py` to export new repositories and dataclasses.
- Create: `alembic/versions/c3d4e5f6a7b8_m37_auth_schema_repositories.py` with the schema migration.
- Modify tests:
  - `tests/unit/db/models/test_auth_models.py`
  - `tests/unit/db/models/test_chat_audit_models.py`
  - `tests/unit/db/repositories/test_auth_repositories.py`
  - `tests/unit/db/repositories/test_knowledge_proposal_repository.py`

## Task 1: Auth Models

**Files:**
- Create: `tests/unit/db/models/test_auth_models.py`
- Create: `src/adaptive_rag/db/models/user.py`
- Modify: `src/adaptive_rag/db/models/__init__.py`

- [ ] **Step 1: Write failing model tests**

Create `tests/unit/db/models/test_auth_models.py` with tests that import `User`, `UserAccessToken`, and `ProjectMembership`, create SQLite tables for `Project` plus the new auth tables, and assert:

```python
def test_user_defaults_to_active_regular_user() -> None:
    user = User(login="viewer@example.com", display_name="Viewer")
    session.add(user)
    session.commit()
    assert user.system_role == "user"
    assert user.is_active is True
```

Also assert unsupported `system_role`, unsupported membership role, duplicate membership, and token hash columns.

- [ ] **Step 2: Verify tests fail for missing models**

Run: `uv run pytest tests\unit\db\models\test_auth_models.py -q`

Expected: FAIL with `ImportError` or `ModuleNotFoundError` for the new model exports.

- [ ] **Step 3: Implement auth models and exports**

Add `src/adaptive_rag/db/models/user.py` defining:

```python
SYSTEM_ROLE_VALUES = ("superadmin", "user")
PROJECT_ROLE_VALUES = ("admin", "contributor", "viewer")

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("system_role IN ('superadmin', 'user')", name="users_system_role_check"),
        UniqueConstraint("login", name="uq_users_login"),
    )
```

Include `id`, `login`, `display_name`, `system_role`, `is_active`, `created_at`, and `updated_at`.

Add `UserAccessToken` with primary key `id`, FK `user_id`, `token_hash`, optional `label`, `expires_at`, `revoked_at`, timestamps, unique `token_hash`, and index on `user_id`.

Add `ProjectMembership` with primary key `id`, FKs `project_id` and `user_id`, role, timestamps, unique `(project_id, user_id)`, indexes `(project_id, role)` and `(user_id, role)`.

Export the classes and constants from `src/adaptive_rag/db/models/__init__.py`.

- [ ] **Step 4: Verify auth model tests pass**

Run: `uv run pytest tests\unit\db\models\test_auth_models.py -q`

Expected: PASS.

## Task 2: Chat Session User Ownership Model

**Files:**
- Modify: `tests/unit/db/models/test_chat_audit_models.py`
- Modify: `src/adaptive_rag/db/models/chat_session.py`

- [ ] **Step 1: Add failing ownership/index tests**

Extend the chat audit model tests so `_make_session()` creates `User.__table__` before `ChatSession.__table__`. Add:

```python
def test_chat_session_can_store_owner_user_id() -> None:
    user = User(login="owner@example.com", display_name="Owner")
    session.add(user)
    session.flush()
    chat_session = ChatSession(project_id=project.id, user_id=user.id)
    ...
    assert fetched.user_id == user.id
```

Update `test_audit_tables_have_project_session_indexes` to assert `("project_id", "user_id", "created_at")` exists on `chat_sessions`.

- [ ] **Step 2: Verify ownership test fails**

Run: `uv run pytest tests\unit\db\models\test_chat_audit_models.py::test_chat_session_can_store_owner_user_id -q`

Expected: FAIL with `TypeError` or missing column for `user_id`.

- [ ] **Step 3: Add nullable `user_id` and index**

Modify `ChatSession`:

```python
user_id: Mapped[UUID | None] = mapped_column(
    ForeignKey("users.id", ondelete="SET NULL"), nullable=True
)
Index("ix_chat_sessions_project_user_created_at", "project_id", "user_id", "created_at")
```

Keep it nullable in this schema slice so existing fixtures and pre-M37 sessions still work until the chat service starts writing current user ids.

- [ ] **Step 4: Verify chat audit model tests pass**

Run: `uv run pytest tests\unit\db\models\test_chat_audit_models.py -q`

Expected: PASS.

## Task 3: User and Membership Repositories

**Files:**
- Create: `tests/unit/db/repositories/test_auth_repositories.py`
- Create: `src/adaptive_rag/db/repositories/users.py`
- Modify: `src/adaptive_rag/db/repositories/__init__.py`

- [ ] **Step 1: Write failing repository tests**

Create tests that build SQLite tables for `Project`, `User`, `UserAccessToken`, and `ProjectMembership`. Cover:

- `UserRepository.create_user()` flushes without committing.
- duplicate login raises `ValueError("user_login_already_exists")`.
- `list_users()` orders by login.
- `upsert_access_token()` stores only token hash and updates label/expiration.
- `ProjectMembershipRepository.upsert_membership()` creates and updates role.
- role normalization rejects unsupported roles.
- `list_project_members()` and `list_user_memberships()` return deterministic order.
- `remove_membership()` returns `True` only when a row existed.

- [ ] **Step 2: Verify repository tests fail for missing repository**

Run: `uv run pytest tests\unit\db\repositories\test_auth_repositories.py -q`

Expected: FAIL with import error for `UserRepository` or `ProjectMembershipRepository`.

- [ ] **Step 3: Implement repositories**

Create `users.py` with:

```python
class UserRepository:
    def create_user(self, *, login: str, display_name: str, system_role: str = "user", is_active: bool = True) -> User: ...
    def get_user(self, user_id: UUID) -> User | None: ...
    def get_by_login(self, login: str) -> User | None: ...
    def list_users(self) -> list[User]: ...
    def update_user(...): ...
    def upsert_access_token(...): ...
    def revoke_access_token(...): ...
    def get_user_by_token_hash(...): ...
```

Create `ProjectMembershipRepository` with `upsert_membership`, `get_membership`, `list_project_members`, `list_user_memberships`, and `remove_membership`. Normalize login/roles and flush without commit.

Export both repositories from `repositories/__init__.py`.

- [ ] **Step 4: Verify repository tests pass**

Run: `uv run pytest tests\unit\db\repositories\test_auth_repositories.py -q`

Expected: PASS.

## Task 4: Knowledge Proposal Model and Repository

**Files:**
- Create: `tests/unit/db/models/test_knowledge_proposal.py`
- Create: `tests/unit/db/repositories/test_knowledge_proposal_repository.py`
- Create: `src/adaptive_rag/db/models/knowledge_proposal.py`
- Create: `src/adaptive_rag/db/repositories/knowledge_proposals.py`
- Modify: `src/adaptive_rag/db/models/__init__.py`
- Modify: `src/adaptive_rag/db/repositories/__init__.py`

- [ ] **Step 1: Write failing model tests**

Test that a proposal persists `project_id`, `submitted_by_user_id`, `origin_session_id`, `origin_message_id`, `proposed_text`, defaults to `pending`, supports `refined_text`, and rejects unsupported statuses.

- [ ] **Step 2: Verify model test fails**

Run: `uv run pytest tests\unit\db\models\test_knowledge_proposal.py -q`

Expected: FAIL with missing model import.

- [ ] **Step 3: Implement model and exports**

Create `KnowledgeProposal` with status values `pending`, `approved`, `rejected`; project/user/session/message/source FKs; text columns; review fields; and indexes on `(project_id, status, created_at)`, `(project_id, submitted_by_user_id, created_at)`, and `(project_id, origin_session_id)`.

- [ ] **Step 4: Verify model test passes**

Run: `uv run pytest tests\unit\db\models\test_knowledge_proposal.py -q`

Expected: PASS.

- [ ] **Step 5: Write failing repository tests**

Cover create pending proposal, list pending by project, list submitted proposals, refine pending proposal, approve pending proposal with reviewer/source id, reject pending proposal with required reason, and reject approve/refine/reject on non-pending proposals.

- [ ] **Step 6: Verify repository test fails**

Run: `uv run pytest tests\unit\db\repositories\test_knowledge_proposal_repository.py -q`

Expected: FAIL with missing repository import.

- [ ] **Step 7: Implement repository**

Create `KnowledgeProposalRepository` with `create`, `get`, `list_by_project`, `list_by_submitter`, `refine`, `approve`, and `reject`. Methods must enforce project scope, pending-only transitions, non-empty rejection reason, and caller-owned transactions.

- [ ] **Step 8: Verify repository tests pass**

Run: `uv run pytest tests\unit\db\repositories\test_knowledge_proposal_repository.py -q`

Expected: PASS.

## Task 5: Alembic Migration

**Files:**
- Create: `alembic/versions/c3d4e5f6a7b8_m37_auth_schema_repositories.py`

- [ ] **Step 1: Write migration after model tests are green**

Create migration with `down_revision = "b2c3d4e5f6a7"`. `upgrade()` must create `users`, `user_access_tokens`, `project_memberships`, add nullable `chat_sessions.user_id`, create the chat session user index, and create `knowledge_proposals`.

- [ ] **Step 2: Validate Alembic head**

Run: `uv run alembic heads`

Expected: `c3d4e5f6a7b8 (head)`.

## Task 6: Focused Validation and Commit

**Files:**
- All files touched in this plan.

- [ ] **Step 1: Run focused tests**

Run:

```powershell
uv run pytest tests\unit\db\models tests\unit\db\repositories -q
```

Expected: all tests pass.

- [ ] **Step 2: Run lint/type checks for touched backend**

Run:

```powershell
uv run ruff check src tests\unit\db\models tests\unit\db\repositories
uv run mypy src\adaptive_rag\db
```

Expected: both pass.

- [ ] **Step 3: Run OpenSpec and diff checks**

Run:

```powershell
npx --yes @fission-ai/openspec validate m37-project-rbac-chat-knowledge --strict
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
git diff --check
```

Expected: OpenSpec passes and diff check exits 0.

- [ ] **Step 4: Commit the slice**

Run:

```powershell
git add src\adaptive_rag\db tests\unit\db alembic\versions\c3d4e5f6a7b8_m37_auth_schema_repositories.py docs\superpowers\plans\2026-06-28-m37-auth-schema-repositories.md
git commit -m "feat: add m37 auth persistence foundation"
```

Expected: commit succeeds on `codex/m37-project-rbac-chat-knowledge`.

## Self-Review

- Spec coverage: this plan covers M37 persistence requirements for local users, project memberships, chat session ownership, and knowledge proposals. API guards, private chat behavior, project admin endpoints, proposal ingestion bridge, and frontend role gating are intentionally later slices listed in the M37 OpenSpec sequence.
- Placeholder scan: no `TBD`, `TODO`, `FIXME`, or unspecified test command remains.
- Type consistency: model and repository names match the planned exports: `User`, `UserAccessToken`, `ProjectMembership`, `KnowledgeProposal`, `UserRepository`, `ProjectMembershipRepository`, and `KnowledgeProposalRepository`.
