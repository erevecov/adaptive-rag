# Provider Secrets Local Key Design

## Goal

Make provider API key storage usable in local development without requiring the
operator to manually export `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY` on every API
restart.

## Decision

Keep `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY` as the highest-priority override for
production and scripted deployments. When it is not configured, the backend
reads a Fernet key from `ADAPTIVE_RAG_PROVIDER_SECRETS_KEY_FILE`, defaulting to
`.adaptive-rag/provider-secrets.key`. If that file does not exist, the backend
creates it with a newly generated Fernet key and reuses it on later restarts.

## Security Boundaries

- The master key is never stored in Postgres.
- The default key file lives under `.adaptive-rag/`, which is ignored by Git.
- Existing encrypted provider secrets remain decryptable only while the same
  master key or key file is preserved.
- Invalid configured keys or invalid key files fail closed with
  `ProviderSecretKeyError`.

## User Flow

For local use, no extra setup is required beyond using the default ignored key
file. The first provider secret save creates the file. For production, set
`ADAPTIVE_RAG_PROVIDER_SECRETS_KEY` explicitly and manage rotation outside the
app.

## Tests

Unit tests cover:

- env key override still encrypts and decrypts secrets;
- missing env key creates and reuses the local key file;
- disabling both env key and key file still raises the stable missing-key error;
- invalid key file content fails closed.
