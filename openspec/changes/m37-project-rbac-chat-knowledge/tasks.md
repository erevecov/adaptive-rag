# Tasks M37 project RBAC chat knowledge

## 1. Planning and setup

- [x] 1.1 Confirm the worktree baseline and create branch
  `codex/m37-project-rbac-chat-knowledge`.
- [x] 1.2 Review current project, chat, authoring and ingestion contracts.
- [x] 1.3 Review BeFlow validation/chat-learning reference behavior.

## 2. OpenSpec change

- [x] 2.1 Add proposal, design and tasks for project RBAC, private chat
  sessions and chat-sourced knowledge proposals.
- [x] 2.2 Add `project-rbac` spec delta for users, memberships and role
  enforcement.
- [x] 2.3 Add `domain-schema` spec delta for users, memberships,
  `chat_sessions.user_id` and `knowledge_proposals`.
- [x] 2.4 Add authoring/project discovery delta.
- [x] 2.5 Add chat history/tool-calling deltas for current-user session
  ownership.
- [x] 2.6 Add ingestion/knowledge proposal delta for approve/reject/refine and
  ingestion bridge.
- [x] 2.7 Add chat frontend delta for project selector, locked project states,
  member management and knowledge review queue.
- [x] 2.8 Update progress and roadmap docs with M37 status and sequence.

## 3. Validation

- [x] 3.1 Run `npx --yes @fission-ai/openspec validate m37-project-rbac-chat-knowledge --strict`.
- [x] 3.2 Run `npx --yes @fission-ai/openspec validate --specs --strict --no-interactive`.
- [x] 3.3 Run `git diff --check`.

## 4. Future implementation slices

- [ ] 4.1 Implement `m37-auth-schema-repositories`.
- [ ] 4.2 Implement `m37-auth-dependencies-api-guards`.
- [ ] 4.3 Implement `m37-private-chat-sessions`.
- [ ] 4.4 Implement `m37-project-admin-users`.
- [ ] 4.5 Implement `m37-knowledge-proposals`.
- [ ] 4.6 Implement `m37-frontend-project-rbac`.
- [ ] 4.7 Run `m37-quality-gate` and archive when complete.
