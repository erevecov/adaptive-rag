# Tasks M39 Qwen runtime production defaults

## 1. Contract

- [x] 1.1 Verify current repo state and active OpenSpec changes.
- [x] 1.2 Verify current Qwen docs through Context7 for OpenAI-compatible chat.
- [x] 1.3 Add OpenSpec proposal/design/tasks and provider-runtime deltas.
- [x] 1.4 Validate the OpenSpec change strictly.

## 2. Qwen defaults and catalog safety

- [x] 2.1 Add failing tests for Qwen model capability inference.
- [x] 2.2 Implement Qwen capability inference in provider model catalog sync.
- [x] 2.3 Verify fake and local model catalog behavior stay unchanged.

## 3. Auto materialize Qwen defaults

- [x] 3.1 Add failing repository/unit tests for idempotent Qwen auto defaults.
- [x] 3.2 Implement Qwen default definitions and auto-default materializer.
- [x] 3.3 Add failing API sync tests for connected-provider auto defaults.
- [x] 3.4 Invoke Qwen auto-default materializer from model sync without overwriting user choices.

## 4. Runtime module organization

- [x] 4.1 Add characterization tests around existing public facade imports.
- [x] 4.2 Split resolution/factory/default code into focused runtime modules.
- [x] 4.3 Keep `adaptive_rag.provider_runtime` as compatibility facade.

## 5. Docs and validation

- [x] 5.1 Document production Qwen auto defaults in runtime acceptance docs.
- [x] 5.2 Run focused backend tests for runtime/model catalog/API.
- [x] 5.3 Run `uv run pytest`, `uv run ruff check src tests`, `uv run mypy src\adaptive_rag`.
- [x] 5.4 Run frontend regression tests if Runtime settings UI text changes.
- [x] 5.5 Run OpenSpec strict and `git diff --check`.
