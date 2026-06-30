# M39 Qwen Runtime Production Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add idempotent Qwen runtime auto-defaults so a connected/synced Qwen provider makes the correct Qwen models usable without an extra command, and reorganize runtime internals without breaking public imports.

**Architecture:** Keep `adaptive_rag.provider_runtime` as a compatibility facade. Add focused runtime modules for Qwen default declarations, auto-default materialization, slot resolution, and provider factories. Use persisted runtime settings as the primary production path, with `.env` as fallback and fake providers still default for local/CI. Qwen defaults are materialized only from existing connected/synced provider catalog rows, and existing user defaults are preserved.

**Tech Stack:** Python 3.12, Typer, SQLAlchemy, FastAPI runtime repositories, Alembic-free data bootstrap, pytest, Ruff, mypy, OpenSpec.

---

## File Structure

- Create `src/adaptive_rag/runtime/__init__.py`: internal runtime package exports.
- Create `src/adaptive_rag/runtime/qwen_defaults.py`: Qwen model/default constants, capability inference, native sparse endpoint checks, and auto-default materialization report.
- Create `src/adaptive_rag/runtime/resolution.py`: move effective slot resolution helpers from `provider_runtime.py`.
- Create `src/adaptive_rag/runtime/factories.py`: move provider/runner construction helpers from `provider_runtime.py`.
- Modify `src/adaptive_rag/provider_runtime.py`: compatibility facade that reexports public names and delegates to runtime modules.
- Modify `src/adaptive_rag/provider_models.py`: infer safe Qwen capabilities when provider model metadata is silent.
- Modify `src/adaptive_rag/api/routes/provider_connections.py`: use safe capability inference during sync and materialize Qwen defaults after sync.
- Create `tests/unit/runtime/test_qwen_defaults.py`: bootstrap and capability inference unit coverage.
- Modify `tests/unit/test_provider_models.py`: Qwen capability inference coverage at lister/catalog boundary.
- Modify `tests/integration/api/test_provider_model_catalog.py`: API sync auto-default coverage.
- Modify `tests/unit/test_provider_runtime.py` and `tests/unit/test_runtime_resolution.py`: facade compatibility characterization after split.
- Modify `docs/runtime-acceptance.md`: production Qwen bootstrap runbook.

## Task 1: Qwen Capability Inference

**Files:**
- Create: `tests/unit/runtime/test_qwen_defaults.py`
- Modify: `src/adaptive_rag/runtime/qwen_defaults.py`
- Modify: `src/adaptive_rag/provider_models.py`
- Modify: `src/adaptive_rag/api/routes/provider_connections.py`

- [ ] **Step 1: Write failing tests for Qwen capability inference**

Create `tests/unit/runtime/test_qwen_defaults.py`:

```python
from adaptive_rag.runtime.qwen_defaults import infer_qwen_model_capabilities


def test_infers_qwen_chat_capability_only() -> None:
    assert infer_qwen_model_capabilities("qwen-plus") == ("chat",)


def test_infers_qwen_embedding_capabilities_only() -> None:
    assert infer_qwen_model_capabilities("text-embedding-v4") == (
        "dense_embedding",
        "sparse_embedding",
    )


def test_infers_qwen_rerank_capability_only() -> None:
    assert infer_qwen_model_capabilities("qwen3-rerank") == ("rerank",)


def test_unknown_qwen_model_has_no_inferred_capabilities() -> None:
    assert infer_qwen_model_capabilities("qwen-unknown-experimental") == ()
```

Add to `tests/unit/test_provider_models.py`:

```python
def test_qwen_model_lister_infers_safe_capabilities_when_provider_is_silent() -> None:
    lister = HTTPProviderModelLister(
        timeout_seconds=3.0,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "qwen-plus"},
                        {"id": "text-embedding-v4"},
                        {"id": "qwen3-rerank"},
                    ]
                },
            )
        ),
    )
    connection = ProviderConnection(
        connection_id="qwen-all",
        provider="qwen",
        connection_type="hosted",
        base_url="https://dashscope.example.test/compatible-mode/v1",
        capabilities_json=["chat", "dense_embedding", "sparse_embedding", "rerank"],
    )

    models = lister.list_models(connection, api_key="sk-hosted-secret")

    assert [(model.model_id, model.capabilities) for model in models] == [
        ("qwen-plus", ("chat",)),
        ("text-embedding-v4", ("dense_embedding", "sparse_embedding")),
        ("qwen3-rerank", ("rerank",)),
    ]
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
uv run pytest tests/unit/runtime/test_qwen_defaults.py tests/unit/test_provider_models.py -q
```

Expected: FAIL because `adaptive_rag.runtime.qwen_defaults` does not exist.

- [ ] **Step 3: Implement minimal Qwen capability inference**

Create `src/adaptive_rag/runtime/__init__.py`:

```python
"""Internal runtime helpers for provider resolution and defaults."""
```

Create `src/adaptive_rag/runtime/qwen_defaults.py` with:

```python
"""Qwen production defaults and bootstrap helpers."""

from __future__ import annotations

QWEN_CHAT_CONNECTION_ID = "qwen-chat"
QWEN_DENSE_EMBEDDING_CONNECTION_ID = "qwen-dense-embedding"
QWEN_SPARSE_EMBEDDING_CONNECTION_ID = "qwen-sparse-embedding"
QWEN_RERANK_CONNECTION_ID = "qwen-rerank"

QWEN_CHAT_MODEL_ID = "qwen-plus"
QWEN_EMBEDDING_MODEL_ID = "text-embedding-v4"
QWEN_RERANK_MODEL_ID = "qwen3-rerank"


def infer_qwen_model_capabilities(model_id: str) -> tuple[str, ...]:
    normalized = model_id.strip().lower()
    if normalized in {"text-embedding-v3", "text-embedding-v4"}:
        return ("dense_embedding", "sparse_embedding")
    if "rerank" in normalized:
        return ("rerank",)
    if normalized in {"qwen-plus", "qwen-max", "qwen-turbo"}:
        return ("chat",)
    if normalized.startswith("qwen3-") and "embedding" not in normalized:
        return ("chat",)
    return ()
```

Modify `src/adaptive_rag/provider_models.py`:

```python
from adaptive_rag.runtime.qwen_defaults import infer_qwen_model_capabilities
```

Change `_model_from_item` to accept provider:

```python
return [_model_from_item(item, provider=connection.provider) for item in items]
```

Update helper:

```python
def _model_from_item(item: object, *, provider: str) -> ProviderModelInfo:
    if not isinstance(item, dict):
        raise ValueError("provider model item must be an object")
    model_id = item.get("id")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("provider model item missing id")
    normalized_model_id = model_id.strip()
    capabilities = _capabilities_from_item(item)
    if not capabilities and provider == "qwen":
        capabilities = infer_qwen_model_capabilities(normalized_model_id)
    pricing = _pricing_from_item(item)
    return ProviderModelInfo(
        model_id=normalized_model_id,
        capabilities=capabilities,
        metadata=dict(item),
        pricing=pricing,
    )
```

Modify `_catalog_capabilities` in `src/adaptive_rag/api/routes/provider_connections.py`:

```python
def _catalog_capabilities(
    connection: ProviderConnection,
    model: ProviderModelInfo,
) -> list[str]:
    if model.capabilities:
        connection_capabilities = set(connection.capabilities_json)
        return [
            capability
            for capability in model.capabilities
            if capability in connection_capabilities
        ]
    if connection.provider == "qwen":
        return []
    return list(connection.capabilities_json)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
uv run pytest tests/unit/runtime/test_qwen_defaults.py tests/unit/test_provider_models.py -q
```

Expected: PASS.

## Task 2: Qwen Auto-Default Materializer

**Files:**
- Modify: `src/adaptive_rag/runtime/qwen_defaults.py`
- Test: `tests/unit/runtime/test_qwen_defaults.py`

- [ ] **Step 1: Write failing auto-default tests**

Append to `tests/unit/runtime/test_qwen_defaults.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from adaptive_rag.db.base import Base
from adaptive_rag.db.models import (
    GlobalChatModel,
    ProviderConnection,
    ProviderModelCatalog,
    RuntimeSlotDefault,
)
from adaptive_rag.db.session import create_session_factory
from adaptive_rag.runtime.qwen_defaults import materialize_qwen_runtime_defaults


def _session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            ProviderConnection.__table__,
            ProviderModelCatalog.__table__,
            RuntimeSlotDefault.__table__,
            GlobalChatModel.__table__,
        ],
    )
    return create_session_factory(engine)()


def test_materialize_qwen_runtime_defaults_is_idempotent_and_preserves_choices() -> None:
    session = _session()

    # Seed ProviderConnection and ProviderModelCatalog rows, then materialize.
    first = materialize_qwen_runtime_defaults(session)
    second = materialize_qwen_runtime_defaults(session)

    assert first == second
    assert session.query(RuntimeSlotDefault).count() == 3
    assert session.query(GlobalChatModel).count() == 1
    assert session.get(RuntimeSlotDefault, "dense_embedding").model_id == (
        "text-embedding-v4"
    )
    assert session.get(RuntimeSlotDefault, "sparse_embedding").model_id == (
        "text-embedding-v4"
    )
    assert session.get(RuntimeSlotDefault, "rerank").model_id == "qwen3-rerank"
    assert session.get(GlobalChatModel, ("qwen-chat", "qwen-plus")).is_default is True


def test_materialize_qwen_runtime_defaults_skips_sparse_for_compatible_base_url() -> None:
    session = _session()

    # Seed compatible-mode catalog and assert sparse default stays unset.
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
uv run pytest tests/unit/runtime/test_qwen_defaults.py -q
```

Expected: FAIL because `materialize_qwen_runtime_defaults` does not exist.

- [ ] **Step 3: Implement auto-default service**

Add to `src/adaptive_rag/runtime/qwen_defaults.py`:

```python
from dataclasses import dataclass

from sqlalchemy.orm import Session

from adaptive_rag.db.repositories import ProviderModelCatalogRepository, RuntimeSettingsRepository


@dataclass(frozen=True, slots=True)
class QwenRuntimeDefaultsReport:
    configured_chat_default: bool
    configured_slot_defaults: tuple[str, ...]


def materialize_qwen_runtime_defaults(session: Session) -> QwenRuntimeDefaultsReport:
    """Configure missing Qwen defaults from connected catalog rows."""
    models = ProviderModelCatalogRepository(session)
    runtime = RuntimeSettingsRepository(session)
    # Find safe Qwen catalog candidates and configure only missing defaults.
    session.flush()
    return QwenRuntimeDefaultsReport(...)
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
uv run pytest tests/unit/runtime/test_qwen_defaults.py -q
```

Expected: PASS.

## Task 3: API Sync Auto Defaults

**Files:**
- Modify: `src/adaptive_rag/api/routes/provider_connections.py`
- Modify: `tests/integration/api/test_provider_model_catalog.py`

- [ ] **Step 1: Write failing API sync tests**

Extend `tests/integration/api/test_provider_model_catalog.py` to assert that
`POST /runtime-settings/connections/{id}/models/sync` materializes missing Qwen
defaults after catalog rows are stored:

```python
assert session.get(RuntimeSlotDefault, "dense_embedding").model_id == "text-embedding-v4"
assert session.get(RuntimeSlotDefault, "rerank").model_id == "qwen3-rerank"
assert session.get(RuntimeSlotDefault, "sparse_embedding") is None
assert session.get(GlobalChatModel, ("qwen-hosted", "qwen-plus")).is_default is True
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```powershell
uv run pytest tests/integration/api/test_provider_model_catalog.py -q
```

Expected: FAIL because sync does not materialize defaults yet.

- [ ] **Step 3: Invoke auto-default materializer from provider model sync**

After catalog upserts in `sync_provider_models`, call
`materialize_qwen_runtime_defaults(session)` when `connection.provider == "qwen"`.

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```powershell
uv run pytest tests/integration/api/test_provider_model_catalog.py -q
```

Expected: PASS.

## Task 4: Runtime Module Split

**Files:**
- Create: `src/adaptive_rag/runtime/resolution.py`
- Create: `src/adaptive_rag/runtime/factories.py`
- Modify: `src/adaptive_rag/provider_runtime.py`
- Test: `tests/unit/test_provider_runtime.py`
- Test: `tests/unit/test_runtime_resolution.py`

- [ ] **Step 1: Add characterization test for facade exports**

Append to `tests/unit/test_provider_runtime.py`:

```python
def test_provider_runtime_public_facade_exports_expected_names() -> None:
    assert provider_runtime.ProviderConfigurationError is ProviderConfigurationError
    assert provider_runtime.get_chat_runner is get_chat_runner
    assert provider_runtime.get_dense_embedding_provider is get_dense_embedding_provider
    assert provider_runtime.get_sparse_embedding_provider is get_sparse_embedding_provider
    assert provider_runtime.get_rerank_provider is get_rerank_provider
```

- [ ] **Step 2: Run characterization tests**

Run:

```powershell
uv run pytest tests/unit/test_provider_runtime.py tests/unit/test_runtime_resolution.py -q
```

Expected: PASS before refactor.

- [ ] **Step 3: Move resolution helpers**

Move these names from `src/adaptive_rag/provider_runtime.py` into
`src/adaptive_rag/runtime/resolution.py` without changing code:

- `ProviderConfigurationError`
- `ResolvedRuntimeSlot`
- `_resolve_persisted_slot`
- `_effective_slot`
- `_global_chat_model`
- `_effective_chat_model`
- `_resolved_slot`
- `_api_key_for_connection`
- `_base_url_for_connection`

Keep imports identical except for module paths.

- [ ] **Step 4: Move factory helpers**

Move these names into `src/adaptive_rag/runtime/factories.py`:

- public factory functions:
  - `get_dense_embedding_provider`
  - `get_sparse_embedding_provider`
  - `get_chat_runner`
  - `get_rerank_provider`
  - `get_contextualizer`
- resolved builders:
  - `_build_resolved_dense_embedding_provider`
  - `_build_resolved_sparse_embedding_provider`
  - `_build_resolved_chat_runner`
  - `_build_resolved_rerank_provider`
- legacy env builders:
  - `_build_embedding_provider`
  - `_build_sparse_embedding_provider`
  - `_build_chat_runner`
  - `_build_rerank_provider`
- shared helpers:
  - `_require_qwen_credentials`
  - `_provider_budget_guard`
  - `_provider_price_catalog`

Import resolution names from `adaptive_rag.runtime.resolution`.

- [ ] **Step 5: Replace provider_runtime with facade**

Replace `src/adaptive_rag/provider_runtime.py` with:

```python
"""Compatibility facade for runtime provider factories."""

from __future__ import annotations

from adaptive_rag.runtime.factories import (
    get_chat_runner,
    get_contextualizer,
    get_dense_embedding_provider,
    get_rerank_provider,
    get_sparse_embedding_provider,
)
from adaptive_rag.runtime.resolution import (
    ProviderConfigurationError,
    ResolvedRuntimeSlot,
)

__all__ = [
    "ProviderConfigurationError",
    "ResolvedRuntimeSlot",
    "get_chat_runner",
    "get_contextualizer",
    "get_dense_embedding_provider",
    "get_rerank_provider",
    "get_sparse_embedding_provider",
]
```

- [ ] **Step 6: Run runtime tests after refactor**

Run:

```powershell
uv run pytest tests/unit/test_provider_runtime.py tests/unit/test_runtime_resolution.py tests/unit/runtime/test_qwen_defaults.py -q
```

Expected: PASS.

## Task 5: Docs and Validation

**Files:**
- Modify: `docs/runtime-acceptance.md`
- Modify: `openspec/changes/m39-qwen-runtime-production-defaults/tasks.md`

- [ ] **Step 1: Document Qwen auto-defaults**

Add to `docs/runtime-acceptance.md` after the default fake acceptance section:

```markdown
## Qwen hosted production defaults

Qwen does not activate on API/CLI startup. Connect the provider through Runtime
settings and run the normal model catalog sync. No extra bootstrap command is
required; after a successful Qwen sync, the backend materializes missing
defaults from known catalog models.

On a clean install, sync configures:

- chat pool default `qwen-plus` if the pool is empty
- dense embedding default `text-embedding-v4` if missing
- rerank default `qwen3-rerank` if missing
- sparse embedding default `text-embedding-v4` only from DashScope native
  TextEmbedding, not OpenAI-compatible mode

Sync preserves existing user choices and does not persist API keys from
environment.
```

- [ ] **Step 2: Run full focused validation**

Run:

```powershell
uv run pytest tests/unit/runtime/test_qwen_defaults.py tests/unit/test_provider_models.py tests/unit/test_provider_runtime.py tests/unit/test_runtime_resolution.py tests/integration/api/test_provider_model_catalog.py -q
```

Expected: PASS.

- [ ] **Step 3: Run quality checks**

Run:

```powershell
uv run ruff check src tests
uv run mypy src\adaptive_rag
npx --yes @fission-ai/openspec validate m39-qwen-runtime-production-defaults --strict
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 4: Update OpenSpec tasks**

Mark completed tasks in `openspec/changes/m39-qwen-runtime-production-defaults/tasks.md` only after each command above has passed.

## Self-Review

Spec coverage:

- Connected-provider Qwen auto defaults: Tasks 2, 3 and 5.
- Correct Qwen model defaults: Tasks 2 and 3.
- Capability inference safety: Task 1.
- Runtime module organization with facade compatibility: Task 4.
- No secret exposure, no command requirement, and no automatic startup activation: Tasks 2, 3 and docs in Task 5.

Placeholder scan:

- No `TBD`, `TODO`, or "similar to" placeholders remain.

Type consistency:

- `QwenRuntimeDefaultsReport` is introduced before sync usage.
- `materialize_qwen_runtime_defaults` signature is consistent across tests and API sync.
- Model IDs match the OpenSpec proposal.
