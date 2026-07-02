# Provider Secrets Local Key Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make provider secret encryption work locally without manually exporting a Fernet master key on every API restart.

**Architecture:** `Settings` gains an optional `provider_secrets_key_file` path. `ProviderSecretStore.from_settings()` keeps the configured env key as the explicit override, otherwise reads or creates the local Fernet key file. The default path is ignored by Git and documented for local use.

**Tech Stack:** Python 3.14 runtime via `uv`, Pydantic settings, `cryptography.Fernet`, pytest.

---

### Task 1: Local Key File Bootstrap

**Files:**
- Modify: `src/adaptive_rag/config/settings.py`
- Modify: `src/adaptive_rag/provider_secrets.py`
- Modify: `tests/unit/test_provider_secrets.py`
- Modify: `.gitignore`
- Modify: `.env.example`
- Modify: `docs/runtime-acceptance.md`

- [ ] **Step 1: Write the failing tests**

Add tests that call `ProviderSecretStore.from_settings()` with no configured
`provider_secrets_key` and a temporary `provider_secrets_key_file`. Assert the
file is created, the encrypted token decrypts after a second store load, and
invalid key file content raises `ProviderSecretKeyError`.

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
uv run pytest tests/unit/test_provider_secrets.py -q
```

Expected before implementation: failure because `Settings` has no
`provider_secrets_key_file` field or `from_settings()` still requires
`ADAPTIVE_RAG_PROVIDER_SECRETS_KEY`.

- [ ] **Step 3: Implement the minimal code**

Add `provider_secrets_key_file: Path | None = Path(".adaptive-rag/provider-secrets.key")`
to `Settings`. In `ProviderSecretStore.from_settings()`, use the env key first;
otherwise read or create the key file with `Fernet.generate_key()`.

- [ ] **Step 4: Document local behavior**

Ignore `.adaptive-rag/`, add `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY_FILE` to
`.env.example`, and update the runtime acceptance runbook.

- [ ] **Step 5: Verify**

Run:

```powershell
uv run pytest tests/unit/test_provider_secrets.py tests/integration/api/test_provider_connections.py tests/integration/api/test_provider_model_catalog.py -q
uv run ruff check src tests
```
