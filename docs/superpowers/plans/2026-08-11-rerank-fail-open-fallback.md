# Rerank Fail-Open Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve bounded baseline retrieval results when optional rerank cannot run for an operational reason, with stable fallback metadata across API, CLI, chat, and audit.

**Architecture:** `RetrievalService` owns the canonical fail-open ranking and metadata policy. Thin API/CLI adapters convert rerank configuration failures into an absent optional provider, while direct runtime factories and hosted eval setup remain strict. Chat audit reads explicit rerank metadata instead of inferring use from metadata presence.

**Tech Stack:** Python 3.12+, dataclasses and typing, SQLAlchemy, FastAPI, Typer, pytest, Ruff, mypy, OpenSpec.

## Global Constraints

- Do not change retrieval, rerank, provider, retry, timeout, or global enablement defaults.
- Do not retry baseline retrieval or call the rerank provider when rerank is disabled.
- Return at most the requested final `limit` while preserving baseline order, fields, citations, strategy metadata, and prior fallback state.
- Operational fallback reasons are exactly `rerank_not_configured`, `rerank_unavailable`, and `rerank_budget_exceeded`.
- Never copy raw provider errors, response bodies, credentials, headers, or request payloads into result metadata.
- Catch only known configuration, budget, provider, and rerank-result contract failures; unexpected exceptions must propagate.
- Direct runtime provider resolution and hosted eval setup remain fail-closed.
- No schema migration, new dependency, frontend change, or deployment configuration is permitted.

---

### Task 1: OpenSpec change contract

**Files:**
- Create: `openspec/changes/rerank-fail-open-fallback/proposal.md`
- Create: `openspec/changes/rerank-fail-open-fallback/design.md`
- Create: `openspec/changes/rerank-fail-open-fallback/tasks.md`
- Create: `openspec/changes/rerank-fail-open-fallback/specs/retrieval-quality/spec.md`
- Create: `openspec/changes/rerank-fail-open-fallback/specs/chat-audit-trail/spec.md`

**Interfaces:**
- Consumes: canonical `retrieval-quality` and `chat-audit-trail` specifications.
- Produces: strict behavioral scenarios for Tasks 2-4.

- [ ] **Step 1: Write the retrieval-quality delta**

```markdown
## ADDED Requirements

### Requirement: Optional rerank fails open to bounded baseline retrieval

The system MUST preserve the already computed baseline retrieval when rerank
cannot complete for an operational reason, and MUST expose a stable secret-safe
fallback reason.

#### Scenario: Missing rerank configuration preserves baseline

- **WHEN** rerank is enabled but its optional provider cannot be configured
- **THEN** retrieval returns the first requested top-k baseline candidates
- **AND** each result reports `rerank_not_configured` and `used_rerank=false`

#### Scenario: Provider and budget failures preserve baseline

- **WHEN** rerank fails through a provider error or budget guard
- **THEN** retrieval returns the bounded baseline order without a second search
- **AND** reports `rerank_unavailable` or `rerank_budget_exceeded` respectively

#### Scenario: Unexpected rerank exception remains visible

- **WHEN** rerank raises an exception outside the known operational contracts
- **THEN** the request fails instead of silently degrading
```

- [ ] **Step 2: Write the chat-audit delta**

```markdown
## ADDED Requirements

### Requirement: Rerank fallback remains auditable

The system MUST distinguish successful rerank from rerank fallback in durable
chat audit data without requiring a schema migration.

#### Scenario: Fallback metadata does not imply successful rerank

- **WHEN** a retrieval result contains rerank fallback metadata
- **THEN** the retrieval run stores `used_rerank=false`
- **AND** the tool result summary stores `rerank_fallback_reason`
- **AND** a pre-existing top-level fallback reason remains unchanged
```

- [ ] **Step 3: Write proposal, design, and task checklist**

The proposal states the availability problem, selected service-level policy,
three public reason codes, unchanged strict runtime/eval behavior, and required
validation. The OpenSpec design links to
`docs/superpowers/specs/2026-08-11-rerank-fail-open-fallback-design.md` and
restates the exact data flow and non-goals. The tasks file mirrors Tasks 2-5 of
this plan with unchecked boxes.

- [ ] **Step 4: Validate the active change**

Run:

```bash
npx --yes @fission-ai/openspec validate rerank-fail-open-fallback --strict
```

Expected: the change is valid with no missing scenarios or malformed deltas.

- [ ] **Step 5: Commit the OpenSpec contract**

```bash
git add openspec/changes/rerank-fail-open-fallback
git commit -m "docs: specify rerank fail-open fallback"
```

---

### Task 2: Canonical retrieval fallback

**Files:**
- Modify: `src/adaptive_rag/retrieval/service.py:90-700`
- Modify: `tests/unit/retrieval/test_retrieval_service.py:97-1120`

**Interfaces:**
- Consumes: `RetrievalRerankOptions`, `RerankProviderError`, `ProviderBudgetExceededError`, and baseline `RetrievalSearchResult` values.
- Produces: `RerankFallbackReason`, `_fallback_rerank_results`, and fallback result metadata consumed by every serializer and audit surface.

- [ ] **Step 1: Replace the missing-provider error test with a failing fallback test**

Create two dense candidates, request `limit=1` and `candidate_limit=2` without a
reranker, then assert:

```python
assert [result.chunk_id for result in results] == [near.id]
assert results[0].fallback_reason == "rerank_not_configured"
assert results[0].rerank_metadata == {
    "candidate_limit": 2,
    "fallback_reason": "rerank_not_configured",
    "used_rerank": False,
}
```

- [ ] **Step 2: Convert provider and budget tests into failing fallback assertions**

Use `FailingRerankProvider` and `BudgetBlockedRerankProvider`; for each, assert
that the baseline chunk is returned and metadata contains respectively
`rerank_unavailable` and `rerank_budget_exceeded` with `used_rerank=False`.

- [ ] **Step 3: Add failing result-contract and unexpected-exception tests**

Add providers that return an empty score tuple, duplicate candidate IDs, and an
unknown candidate ID. Each must degrade to `rerank_unavailable`. Add a provider
that raises `RuntimeError("programming defect")` and assert that exact exception
propagates.

- [ ] **Step 4: Add a failing prior-fallback preservation test**

Pass a baseline result with
`fallback_reason="graph_projection_pending_backfill"` through rerank fallback
and assert the top-level reason stays unchanged while
`rerank_metadata["fallback_reason"] == "rerank_unavailable"`.

- [ ] **Step 5: Run RED tests**

Run:

```bash
uv run --extra dev pytest -q tests/unit/retrieval/test_retrieval_service.py -k "rerank"
```

Expected: new fallback tests fail because current code raises
`RetrievalServiceError` or lacks fallback metadata; the existing success test
continues to pass.

- [ ] **Step 6: Implement the minimal service policy**

Add:

```python
RerankFallbackReason = Literal[
    "rerank_not_configured",
    "rerank_unavailable",
    "rerank_budget_exceeded",
]

class _RerankResultValidationError(ValueError):
    pass
```

Remove the reranker-presence check from `_validate_rerank_options`. In
`_rerank_results`, use this exact missing-provider branch when
`self._reranker is None`:

```python
return _fallback_rerank_results(
    results,
    limit=limit,
    candidate_limit=options.candidate_limit,
    reason="rerank_not_configured",
)
```

Map budget and provider errors to their codes; wrap only known
`_apply_rerank_result` validation errors as `rerank_unavailable`.

Implement the copy helper with this exact policy:

```python
def _fallback_rerank_results(
    results: list[RetrievalSearchResult],
    *,
    limit: int,
    candidate_limit: int,
    reason: RerankFallbackReason,
) -> list[RetrievalSearchResult]:
    return [
        RetrievalSearchResult(
            chunk_id=result.chunk_id,
            distance=result.distance,
            score=result.score,
            citation=result.citation,
            embedding_metadata=_copy_metadata(result.embedding_metadata),
            retrieval_metadata=_copy_metadata(result.retrieval_metadata),
            rerank_metadata={
                "candidate_limit": candidate_limit,
                "fallback_reason": reason,
                "used_rerank": False,
            },
            strategy=result.strategy,
            fallback_reason=result.fallback_reason or reason,
        )
        for result in results[:limit]
    ]
```

- [ ] **Step 7: Run GREEN retrieval tests**

```bash
uv run --extra dev pytest -q tests/unit/retrieval/test_retrieval_service.py
```

Expected: all retrieval service tests pass with no warnings.

- [ ] **Step 8: Commit the canonical fallback**

```bash
git add src/adaptive_rag/retrieval/service.py tests/unit/retrieval/test_retrieval_service.py
git commit -m "feat: fail open when rerank is unavailable"
```

---

### Task 3: Configuration fail-open adapters for API and CLI

**Files:**
- Modify: `src/adaptive_rag/api/dependencies.py:35-222`
- Modify: `src/adaptive_rag/cli/retrieval.py:1-187`
- Modify: `src/adaptive_rag/cli/chat.py:1-360`
- Create: `tests/unit/test_api_dependencies.py`
- Modify: `tests/integration/api/test_retrieval.py`
- Modify: `tests/integration/cli/test_retrieval_cli.py`
- Modify: `tests/integration/cli/test_chat_cli.py`

**Interfaces:**
- Consumes: strict `get_rerank_provider(...)` factories and `ProviderConfigurationError`.
- Produces: optional `RerankProvider | None` values for product retrieval only.

- [ ] **Step 1: Add a failing API factory test**

Monkeypatch `adaptive_rag.api.dependencies.get_runtime_rerank_provider` to raise
`ProviderConfigurationError("missing_provider_secret")`, build the callable
from `get_rerank_provider_factory()`, and assert `factory() is None`. Add a
control test returning a sentinel reranker and assert identity is preserved.

- [ ] **Step 2: Add a failing retrieval API fallback test**

Override `get_rerank_provider_factory` with a callable that returns `None`,
send a request with `limit=1` and `candidate_limit=2`, and assert HTTP 200,
baseline order, top-level `rerank_not_configured`, and
`rerank_metadata["used_rerank"] is False`.

- [ ] **Step 3: Add failing CLI retrieval and chat tests**

Patch each CLI module's `get_cli_rerank_provider` to raise
`ProviderConfigurationError("missing_provider_secret")`. Invoke retrieval and
chat with effective rerank enabled, then assert exit code `0`, preserved
baseline citations/results, `fallback_reason="rerank_not_configured"`, and
`rerank_metadata["used_rerank"] is False`.

- [ ] **Step 4: Run RED adapter tests**

```bash
uv run --extra dev pytest -q tests/unit/test_api_dependencies.py tests/integration/api/test_retrieval.py tests/integration/cli/test_retrieval_cli.py tests/integration/cli/test_chat_cli.py -k "rerank and (configuration or not_configured)"
```

Expected: configuration errors currently propagate and make the commands fail.

- [ ] **Step 5: Implement optional product adapters**

Change the API alias and factory closure to:

```python
RerankProviderFactory = Callable[[], RerankProvider | None]

def build() -> RerankProvider | None:
    try:
        return cast(
            RerankProvider,
            _call_with_supported_kwargs(
                get_runtime_rerank_provider,
                workspace_id=workspace_id,
                session=active_session,
                usage_tracker=active_usage_tracker,
            ),
        )
    except ProviderConfigurationError:
        return None
```

Apply the same narrow catch inside `_get_rerank_provider` and
`_get_chat_rerank_provider`, update their return types to
`RerankProvider | None`, and update `_LazyCliChatRetrievalSearcher`'s factory
type accordingly. Do not catch provider errors from dense or sparse factories.

- [ ] **Step 6: Run GREEN adapter and surface tests**

```bash
uv run --extra dev pytest -q tests/unit/test_api_dependencies.py tests/integration/api/test_retrieval.py tests/integration/api/test_chat.py tests/integration/cli/test_retrieval_cli.py tests/integration/cli/test_chat_cli.py
```

Expected: configuration fallback and all existing successful rerank cases pass.

- [ ] **Step 7: Commit adapters**

```bash
git add src/adaptive_rag/api/dependencies.py src/adaptive_rag/cli/retrieval.py src/adaptive_rag/cli/chat.py tests/unit/test_api_dependencies.py tests/integration/api/test_retrieval.py tests/integration/cli/test_retrieval_cli.py tests/integration/cli/test_chat_cli.py
git commit -m "feat: degrade missing rerank configuration"
```

---

### Task 4: Audit and chat fallback semantics

**Files:**
- Modify: `src/adaptive_rag/chat/audit.py:696-970`
- Modify: `tests/unit/db/repositories/test_chat_audit_repository.py`
- Modify: `tests/integration/api/test_chat.py`

**Interfaces:**
- Consumes: serialized `rerank_metadata.used_rerank` and `rerank_metadata.fallback_reason` from Task 2.
- Produces: accurate `RetrievalRun.used_rerank` and `result_summary_json.rerank_fallback_reason`.

- [ ] **Step 1: Add failing durable audit writer coverage**

Extend the existing SQL audit writer score-breakdown test with
`rerank_metadata={"fallback_reason": "rerank_unavailable",
"used_rerank": False}` and top-level
`fallback_reason="graph_projection_pending_backfill"`. Assert the persisted
retrieval run and tool summary contain:

```python
assert retrieval_runs[0].used_rerank is False
assert retrieved_chunks[0].rerank_score is None
assert summary["fallback_reason"] == "graph_projection_pending_backfill"
assert summary["rerank_fallback_reason"] == "rerank_unavailable"
```

Update the existing successful score-breakdown fixture to include
`"used_rerank": True`, preserving its successful audit assertion.

- [ ] **Step 2: Add a failing durable chat audit test**

Execute a chat turn with a reranker that raises `RerankProviderError`, then
assert HTTP 200, baseline citation returned, `RetrievalRun.used_rerank is
False`, `RetrievedChunk.rerank_score is None`, and the tool-call result summary
contains `rerank_fallback_reason="rerank_unavailable"`.

- [ ] **Step 3: Run RED audit tests**

```bash
uv run --extra dev pytest -q tests/unit/db/repositories/test_chat_audit_repository.py tests/integration/api/test_chat.py -k "rerank and fallback"
```

Expected: current audit infers `used_rerank=True` from metadata presence and
does not emit the stage-specific summary field.

- [ ] **Step 4: Implement explicit audit extraction**

Replace the presence check with helpers equivalent to:

```python
def _used_rerank(results: Sequence[RetrievalResultPayload]) -> bool:
    return any(
        result.get("rerank_metadata", {}).get("used_rerank") is True
        for result in results
    )

def _rerank_fallback_reason(
    results: Sequence[RetrievalResultPayload],
) -> str | None:
    for result in results:
        value = result.get("rerank_metadata", {}).get("fallback_reason")
        if isinstance(value, str):
            return value
    return None
```

Use `_used_rerank(results)` when creating `RetrievalRun`. Add
`rerank_fallback_reason` to `_retrieval_result_summary` only when present.

- [ ] **Step 5: Run GREEN chat and audit tests**

```bash
uv run --extra dev pytest -q tests/unit/chat tests/unit/db/repositories/test_chat_audit_repository.py tests/integration/api/test_chat.py
```

Expected: chat succeeds on rerank fallback and durable audit remains accurate.

- [ ] **Step 6: Commit audit behavior**

```bash
git add src/adaptive_rag/chat/audit.py tests/unit/db/repositories/test_chat_audit_repository.py tests/integration/api/test_chat.py
git commit -m "fix: audit rerank fallback explicitly"
```

---

### Task 5: Full verification and contract closeout

**Files:**
- Modify: `openspec/changes/rerank-fail-open-fallback/tasks.md`
- Verify: all files changed in Tasks 1-4.

**Interfaces:**
- Consumes: complete implementation and active OpenSpec change.
- Produces: checked task evidence with no unverified completion claim.

- [ ] **Step 1: Run focused regression suites**

```bash
uv run --extra dev pytest -q tests/unit/retrieval tests/unit/chat tests/unit/test_api_dependencies.py tests/unit/test_provider_runtime.py tests/integration/api/test_retrieval.py tests/integration/api/test_chat.py tests/integration/cli/test_retrieval_cli.py tests/integration/cli/test_chat_cli.py
```

Expected: all focused tests pass.

- [ ] **Step 2: Run static checks**

```bash
uv run --extra dev ruff format --check .
uv run --extra dev ruff check .
uv run --extra dev mypy
git diff --check
```

Expected: every command exits zero with no diagnostics.

- [ ] **Step 3: Validate OpenSpec**

```bash
npx --yes @fission-ai/openspec validate rerank-fail-open-fallback --strict
npx --yes @fission-ai/openspec validate --specs --strict --no-interactive
```

Expected: active change and canonical specs are valid.

- [ ] **Step 4: Run the full test suite**

```bash
uv run --extra dev pytest
```

Expected: the full suite passes with zero failures.

- [ ] **Step 5: Mark only verified OpenSpec tasks complete and commit**

Update checkboxes whose commands passed, then run:

```bash
git add openspec/changes/rerank-fail-open-fallback/tasks.md
git commit -m "test: verify rerank fail-open fallback"
```

- [ ] **Step 6: Review final scope**

```bash
git status --short
git diff origin/main...HEAD --stat
git log --oneline origin/main..HEAD
```

Expected: only the design, plan, OpenSpec change, retrieval fallback, adapters,
audit behavior, and their tests appear; no unrelated files are modified.
