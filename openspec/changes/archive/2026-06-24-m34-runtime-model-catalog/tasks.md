# Tasks M34 runtime model catalog

## 1. Research and contract

- [x] 1.1 Verify current repo state, previous PR merge and active OpenSpec
  changes.
- [x] 1.2 Check current Qwen/DashScope docs for model listing and pricing
  metadata behavior.
- [x] 1.3 Add OpenSpec deltas for provider-runtime and chat-frontend.

## 2. Backend

- [x] 2.1 Add provider model catalog SQLAlchemy model and Alembic migration.
- [x] 2.2 Add repository methods for generated connection IDs and model catalog
  upsert/list.
- [x] 2.3 Add provider model lister for OpenAI-compatible Qwen/local endpoints
  and fake catalog fallback.
- [x] 2.4 Add APIs for POST connection create, GET model catalog and POST model
  sync.

## 3. Frontend

- [x] 3.1 Extend API client types and methods for generated connections and
  model catalog.
- [x] 3.2 Refresh Runtime settings with connections, slots, chat models and
  model catalog together.
- [x] 3.3 Replace manual connection/model ID inputs with selectors.
- [x] 3.4 Add model sync control and catalog display metadata/pricing summary.

## 4. Validation

- [x] 4.1 Run focused RED/GREEN backend and frontend tests.
- [x] 4.2 Run full backend/frontend quality gates.
- [x] 4.3 Run rendered Runtime settings QA in browser.
- [x] 4.4 Update progress/roadmap and create PR.
