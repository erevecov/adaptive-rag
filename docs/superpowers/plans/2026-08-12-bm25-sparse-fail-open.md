# BM25 Sparse Fail-Open Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When neural sparse is missing or fails, retrieval fail-opens to Okapi BM25 (BM25-only for `sparse`, dense+BM25 RRF for `dense_sparse`) with stable secret-safe `fallback_reason` codes.

**Architecture:** All fail-open policy lives in `RetrievalService`. RRF fusion gains an optional BM25 leg. Thin API/CLI/chat adapters that build the sparse provider must convert configuration failures into `sparse_provider=None` so the service can fall back (mirrors rerank fail-open). Explicit `bm25` / `lexical` / `hybrid_rrf` / `dense` / `graph` paths stay unchanged.

**Tech Stack:** Python 3.12+, SQLAlchemy, FastAPI, pytest, existing `Bm25Retriever` / RRF helpers.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-12-bm25-sparse-fail-open-design.md`
- Happy path stays dense + sparse RRF when sparse provider is present and succeeds.
- Fake sparse provider counts as configured (offline/dev smoke).
- Fail-open applies to strategies `sparse` and `dense_sparse` only.
- Fallback reason codes are exactly: `sparse_provider_unavailable`, `sparse_provider_error`, `sparse_query_embed_failed`, `sparse_retrieval_failed`.
- Never copy raw provider errors, credentials, or response bodies into metadata.
- Unexpected exceptions outside sparse/provider operational failures must still propagate (especially dense failures).
- No schema migration, no new dependencies, no ingest `embedding_mode` change.
- Public request strategy name for chat default remains `dense_sparse`; report effective `strategy=bm25` only when the request was `sparse` and fell back.

## File map

| File | Responsibility |
|------|----------------|
| `src/adaptive_rag/retrieval/service.py` | Sparse try/fallback, BM25 RRF leg, reason codes |
| `src/adaptive_rag/api/dependencies.py` | `LazyChatRetrievalSearcher` catch config errors → `None` |
| `src/adaptive_rag/api/routes/retrieval.py` | Same provider build fail-open if it constructs sparse eagerly |
| `src/adaptive_rag/cli/retrieval.py` / evals adapters | Same if they raise before `RetrievalService` |
| `tests/unit/retrieval/test_retrieval_service.py` | Core contract tests |
| `tests/unit/test_api_dependencies.py` or chat retrieval unit | Lazy factory fail-open |
| `docs/architecture/bm25-qwen-sparse-comparison.md` | Note fail-open behavior |
| Optional OpenSpec delta under `openspec/changes/bm25-sparse-fail-open/` | If repo Gate expects it for retrieval-quality |

---

### Task 1: Unit tests for sparse → BM25 fail-open (TDD)

**Files:**
- Modify: `tests/unit/retrieval/test_retrieval_service.py`
- Modify: `src/adaptive_rag/retrieval/service.py` (later tasks make these pass)

**Interfaces:**
- Consumes: `RetrievalService`, `RetrievalSearchRequest`, existing DB fixtures in that file
- Produces: failing tests that lock the contract for Tasks 2–4

- [ ] **Step 1: Replace the hard-fail sparse-provider test with fail-open expectations**

Find `test_retrieval_service_requires_sparse_provider_for_sparse_strategies` and change it so `sparse_provider=None` no longer raises.

```python
@pytest.mark.parametrize("strategy", ["sparse", "dense_sparse"])
def test_retrieval_service_falls_back_to_bm25_when_sparse_provider_missing(
    strategy: str,
) -> None:
    session = _session_with_chunk_corpus()  # use the file's existing fixture helper
    service = RetrievalService(session, provider=_dense_provider(), sparse_provider=None)
    results = service.search(
        RetrievalSearchRequest(
            workspace_id=WORKSPACE_ID,
            query="SKU-42 installation",
            limit=5,
            strategy=strategy,  # type: ignore[arg-type]
        )
    )
    assert results
    assert all(r.fallback_reason == "sparse_provider_unavailable" for r in results)
    if strategy == "sparse":
        assert all(r.strategy == "bm25" for r in results)
        assert results[0].retrieval_metadata["used_bm25"] is True
    else:
        assert all(r.strategy == "dense_sparse" for r in results)
        assert "bm25" in results[0].retrieval_metadata["source_strategies"]
        assert "dense" in results[0].retrieval_metadata["source_strategies"]
```

Adapt `_session_with_chunk_corpus` / provider helpers to whatever names already exist in the file (mirror `test_retrieval_service_uses_bm25_strategy_without_embedding_query` and `test_retrieval_service_fuses_dense_and_sparse_with_rrf` setup).

- [ ] **Step 2: Add embed-failure and retrieval-failure tests**

```python
class RaisingSparseEmbedProvider(StaticSparseEmbeddingProvider):
    def embed_query(self, text: str) -> SparseEmbeddingVector:
        self.query_inputs.append(text)
        raise RuntimeError("sparse embed boom")


def test_retrieval_service_falls_back_when_sparse_query_embed_fails() -> None:
    # session + dense corpus + optional sparse rows as in dense_sparse happy test
    service = RetrievalService(
        session,
        provider=dense_provider,
        sparse_provider=RaisingSparseEmbedProvider(query_vector=...),
    )
    results = service.search(
        RetrievalSearchRequest(
            workspace_id=WORKSPACE_ID,
            query="SKU-42 installation",
            limit=5,
            strategy="dense_sparse",
        )
    )
    assert results
    assert results[0].fallback_reason == "sparse_query_embed_failed"
    assert "bm25" in results[0].retrieval_metadata["source_strategies"]


class RaisingSparseSearchProvider(StaticSparseEmbeddingProvider):
    def embed_query(self, text: str) -> SparseEmbeddingVector:
        self.query_inputs.append(text)
        return self.query_vector


# Monkeypatch SparseRetriever.search to raise SparseRetrievalError, OR
# use a provider that embeds OK but no sparse rows + inject a stub retriever
# if the service allows — prefer catching SparseRetrievalError from
# _raw_sparse_results path by subclassing RetrievalService in the test only
# if needed. Prefer: patch service._sparse_retriever.search to raise
# SparseRetrievalError("index failed").


def test_retrieval_service_falls_back_when_sparse_retrieval_fails(monkeypatch) -> None:
    ...
    assert results[0].fallback_reason == "sparse_retrieval_failed"
```

- [ ] **Step 3: Keep happy-path dense_sparse test green (no fallback_reason)**

Assert existing `test_retrieval_service_fuses_dense_and_sparse_with_rrf` still expects `fallback_reason is None` and `source_strategies == ["dense", "sparse"]`.

- [ ] **Step 4: Run tests — expect FAIL on new/changed cases**

Run: `cd /Users/ereveco/.cursor/worktrees/adaptive-rag/4nsf && uv run pytest tests/unit/retrieval/test_retrieval_service.py -k 'sparse_provider_missing or sparse_query_embed or sparse_retrieval_fails or fuses_dense_and_sparse' -v`

Expected: new fail-open tests FAIL (still raise `RetrievalServiceError` or missing BM25 fusion).

- [ ] **Step 5: Commit tests only if you prefer red commits; otherwise proceed to Task 2 before committing**

```bash
git add tests/unit/retrieval/test_retrieval_service.py
git commit -m "$(cat <<'EOF'
test(retrieval): specify sparse-to-bm25 fail-open contract

EOF
)"
```

---

### Task 2: Extend RRF fusion to accept BM25 legs

**Files:**
- Modify: `src/adaptive_rag/retrieval/service.py` (`_fuse_rrf_results`, `_RRFAccumulator`, `_to_rrf_search_result`, `_rrf_source_strategies`)

**Interfaces:**
- Consumes: `Bm25RetrievalResult` from `adaptive_rag.retrieval.bm25`
- Produces: `_fuse_rrf_results(..., bm25_results=Sequence[Bm25RetrievalResult]=())` usable by Task 3

- [ ] **Step 1: Extend accumulator**

```python
@dataclass(slots=True)
class _RRFAccumulator:
    chunk_id: UUID
    rrf_score: float = 0.0
    dense_rank: int | None = None
    lexical_rank: int | None = None
    sparse_rank: int | None = None
    bm25_rank: int | None = None
    dense_result: DenseRetrievalResult | None = None
    lexical_result: LexicalRetrievalResult | None = None
    sparse_result: SparseRetrievalResult | None = None
    bm25_result: Bm25RetrievalResult | None = None
```

- [ ] **Step 2: Fuse BM25 ranks like lexical/sparse**

In `_fuse_rrf_results`, add parameter `bm25_results: Sequence[Bm25RetrievalResult] = ()` and loop:

```python
for rank, bm25_result in enumerate(bm25_results, start=1):
    accumulator = by_chunk_id.setdefault(
        bm25_result.chunk_id,
        _RRFAccumulator(chunk_id=bm25_result.chunk_id),
    )
    accumulator.bm25_result = bm25_result
    accumulator.bm25_rank = rank
    accumulator.rrf_score += _rrf_score(rank)
```

Include `bm25_rank` in the sort tie-break tuple (after sparse_rank).

- [ ] **Step 3: Metadata + source_strategies**

```python
if accumulator.bm25_result is not None and accumulator.bm25_rank is not None:
    metadata["bm25_rank"] = accumulator.bm25_rank
    metadata["bm25_score"] = accumulator.bm25_result.score
    metadata["used_bm25"] = True

# in _rrf_source_strategies:
if accumulator.bm25_result is not None:
    strategies.append("bm25")
```

Update `_to_rrf_search_result` source fallback chain:

```python
source = (
    accumulator.dense_result
    or accumulator.lexical_result
    or accumulator.sparse_result
    or accumulator.bm25_result
)
```

- [ ] **Step 4: Run fusion-related unit tests**

Run: `uv run pytest tests/unit/retrieval/test_retrieval_service.py -k 'rrf or bm25 or dense_and_sparse' -v`  
Expected: existing hybrid/dense_sparse still PASS; new fail-open tests may still FAIL until Task 3.

- [ ] **Step 5: Commit**

```bash
git add src/adaptive_rag/retrieval/service.py
git commit -m "$(cat <<'EOF'
feat(retrieval): allow BM25 legs in RRF fusion

EOF
)"
```

---

### Task 3: Sparse try/fallback inside `RetrievalService.search`

**Files:**
- Modify: `src/adaptive_rag/retrieval/service.py`

**Interfaces:**
- Consumes: `_raw_bm25_results`, `_raw_sparse_results`, `_fuse_rrf_results` (with `bm25_results`), `_with_fallback_reason`
- Produces: fail-open behavior for `sparse` / `dense_sparse`

- [ ] **Step 1: Add reason constants and sparse attempt helper**

Near the top of `service.py` (module level):

```python
SPARSE_FALLBACK_UNAVAILABLE = "sparse_provider_unavailable"
SPARSE_FALLBACK_PROVIDER_ERROR = "sparse_provider_error"
SPARSE_FALLBACK_QUERY_EMBED = "sparse_query_embed_failed"
SPARSE_FALLBACK_RETRIEVAL = "sparse_retrieval_failed"
```

Add a private method:

```python
def _try_sparse_results(
    self,
    *,
    workspace_id: UUID,
    query: str,
    limit: int,
    filters: DenseRetrievalFilters,
) -> tuple[list[SparseRetrievalResult] | None, str | None]:
    """Return (sparse_hits, None) or (None, fallback_reason)."""
    if self._sparse_provider is None:
        return None, SPARSE_FALLBACK_UNAVAILABLE
    try:
        query_vector = self._sparse_provider.embed_query(query)
    except Exception:
        # Operational embed/provider failure — no raw message in metadata.
        return None, SPARSE_FALLBACK_QUERY_EMBED
    try:
        hits = self._sparse_retriever.search(
            workspace_id=workspace_id,
            query_vector=query_vector,
            limit=limit,
            filters=filters,
        )
    except SparseRetrievalError:
        return None, SPARSE_FALLBACK_RETRIEVAL
    return hits, None
```

Keep `_raw_sparse_results` for callers that still want hard fail, or refactor it to call `_try_sparse_results` and raise only when used from paths that must not fall open (prefer: only `_try_sparse_results` used from `search` for sparse strategies).

- [ ] **Step 2: Remove the hard require at the start of `search`**

Delete:

```python
if strategy in ("sparse", "dense_sparse") and self._sparse_provider is None:
    raise RetrievalServiceError(...)
```

- [ ] **Step 3: Rewrite `sparse` and `dense_sparse` branches**

For `strategy == "sparse"`:

```python
sparse_hits, reason = self._try_sparse_results(...)
if sparse_hits is not None:
    search_results = [_to_sparse_search_result(r) for r in sparse_hits]
else:
    search_results = [
        _with_fallback_reason(result, reason or SPARSE_FALLBACK_UNAVAILABLE)
        for result in self._bm25_results(...)
    ]
```

For `strategy == "dense_sparse"` (after dense succeeds):

```python
sparse_hits, reason = self._try_sparse_results(...)
if sparse_hits is not None:
    search_results = _fuse_rrf_results(
        dense_results=dense_results,
        sparse_results=sparse_hits,
        limit=candidate_limit,
        strategy="dense_sparse",
    )
else:
    bm25_hits = self._raw_bm25_results(...)
    search_results = _fuse_rrf_results(
        dense_results=dense_results,
        bm25_results=bm25_hits,
        limit=candidate_limit,
        strategy="dense_sparse",
    )
    search_results = [
        _with_fallback_reason(result, reason or SPARSE_FALLBACK_UNAVAILABLE)
        for result in search_results
    ]
```

Map bare `Exception` from provider construction is **not** here — that is Task 4. If embed raises a typed provider config error class that exists in-repo, map it to `SPARSE_FALLBACK_PROVIDER_ERROR` instead of `sparse_query_embed_failed` when appropriate (check Qwen/client error types; if only `RuntimeError`/`Exception`, `sparse_query_embed_failed` is enough for embed path).

- [ ] **Step 4: Run unit retrieval tests**

Run: `uv run pytest tests/unit/retrieval/test_retrieval_service.py -v`  
Expected: PASS including new fail-open cases; graph/rerank tests unchanged.

- [ ] **Step 5: Commit**

```bash
git add src/adaptive_rag/retrieval/service.py tests/unit/retrieval/test_retrieval_service.py
git commit -m "$(cat <<'EOF'
feat(retrieval): fail open from sparse to Okapi BM25

EOF
)"
```

---

### Task 4: Adapter fail-open when sparse factory cannot configure

**Files:**
- Modify: `src/adaptive_rag/api/dependencies.py` (`LazyChatRetrievalSearcher.search`)
- Modify: `src/adaptive_rag/api/routes/retrieval.py` (if it builds sparse provider eagerly)
- Modify: `src/adaptive_rag/cli/retrieval.py` and any eval runner that constructs `RetrievalService` with a factory that can raise `ProviderConfigurationError`
- Test: `tests/unit/test_api_dependencies.py` (extend) or new test next to chat retrieval helpers

**Interfaces:**
- Consumes: `ProviderConfigurationError` from `adaptive_rag.provider_runtime`
- Produces: `RetrievalService(..., sparse_provider=None)` when config is incomplete so Task 3 fallback runs

- [ ] **Step 1: Wrap sparse factory in LazyChatRetrievalSearcher**

```python
def search(self, request: RetrievalSearchRequest) -> list[RetrievalSearchResult]:
    sparse_provider = None
    if request.strategy in ("sparse", "dense_sparse"):
        try:
            sparse_provider = self._sparse_provider_factory()
        except ProviderConfigurationError:
            sparse_provider = None
    service = RetrievalService(
        self._session,
        provider=self._provider,
        sparse_provider=sparse_provider,
        ...
    )
    return service.search(request)
```

- [ ] **Step 2: Mirror the same try/except in API retrieval route / CLI** wherever `get_sparse_embedding_provider` is called only because strategy is sparse-touching. Do **not** change `get_default_sparse_embedding_provider` itself to swallow errors (ingest/evals that require live sparse stay strict when they opt into `--require-live-qwen-sparse`).

- [ ] **Step 3: Unit test for lazy searcher**

```python
def test_lazy_chat_retrieval_searcher_treats_sparse_config_error_as_absent(
    monkeypatch,
) -> None:
    def boom() -> SparseEmbeddingProvider:
        raise ProviderConfigurationError("ADAPTIVE_RAG_SPARSE_EMBEDDING_MODEL must be set")

    searcher = LazyChatRetrievalSearcher(
        session=session,
        provider=dense_provider,
        sparse_provider_factory=boom,
        rerank_provider_factory=lambda: None,
        graph_retriever=None,
    )
    results = searcher.search(
        RetrievalSearchRequest(
            workspace_id=WORKSPACE_ID,
            query="alpha",
            limit=3,
            strategy="dense_sparse",
        )
    )
    assert results
    assert results[0].fallback_reason == "sparse_provider_unavailable"
```

- [ ] **Step 4: Run targeted tests**

Run: `uv run pytest tests/unit/retrieval/test_retrieval_service.py tests/unit/test_api_dependencies.py -v`  
Plus any new lazy-searcher test file path you create.

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/adaptive_rag/api/dependencies.py src/adaptive_rag/api/routes/retrieval.py src/adaptive_rag/cli/retrieval.py tests/unit/test_api_dependencies.py
git commit -m "$(cat <<'EOF'
fix(retrieval): treat sparse config errors as absent provider

EOF
)"
```

---

### Task 5: Docs + architecture note + verify suite smoke

**Files:**
- Modify: `docs/architecture/bm25-qwen-sparse-comparison.md`
- Modify: `docs/superpowers/specs/2026-08-12-bm25-sparse-fail-open-design.md` (status already approved; fix any “TBD” reason strings to match constants)
- Optional: OpenSpec change `openspec/changes/bm25-sparse-fail-open/` if Gate 1 is required before merge in this repo — copy scenarios from Task 1 into `specs/retrieval-quality/spec.md` ADDED requirements with SHALL wording

- [ ] **Step 1: Document fail-open in architecture note**

Add a short section:

```markdown
## Fail-open (2026-08-12)

`sparse` and `dense_sparse` fail open to Okapi BM25 when the sparse provider
is not configured or fails at query embed / sparse retrieval time.

- `dense_sparse` → dense + BM25 RRF, request strategy stays `dense_sparse`,
  `fallback_reason` set, `source_strategies` includes `bm25`.
- `sparse` → BM25-only with effective `strategy=bm25` and `fallback_reason`.
- Explicit `strategy=bm25` remains opt-in without dense.
```

- [ ] **Step 2: Run broader verification**

Run:

```bash
uv run pytest tests/unit/retrieval/test_retrieval_service.py tests/integration/api/test_retrieval.py -q
```

Expected: PASS (update any integration assertion that still expects HTTP 4xx/5xx when sparse provider is missing for `dense_sparse`/`sparse`).

- [ ] **Step 3: Commit docs (+ OpenSpec if added)**

```bash
git add docs/architecture/bm25-qwen-sparse-comparison.md docs/superpowers/specs/2026-08-12-bm25-sparse-fail-open-design.md openspec/changes/bm25-sparse-fail-open
git commit -m "$(cat <<'EOF'
docs(retrieval): document sparse-to-bm25 fail-open behavior

EOF
)"
```

---

## Spec coverage checklist

| Spec requirement | Task |
|------------------|------|
| Dense+sparse when configured & OK | Task 3 (happy path preserved) + existing test |
| BM25 substitute when not configured | Tasks 1–3 |
| Fail-open on provider/embed/retrieval failure | Tasks 1, 3 |
| Applies to `sparse` and `dense_sparse` | Tasks 1, 3 |
| `fallback_reason` codes | Tasks 1, 3 |
| Effective `bm25` strategy for `sparse` fallback | Task 3 |
| Chat/API inherit via adapters | Task 4 |
| No ingest / hybrid_rrf / explicit bm25 change | Global constraints |
| Docs | Task 5 |

## Placeholder scan

No TBD remaining for reason codes (locked in Global Constraints). OpenSpec is optional and called out explicitly.
