## ADDED Requirements

### Requirement: Secret-like content is redacted by a shared content guard

The system MUST provide a deterministic heuristic content guard that detects
common secret-like patterns in plain text and redacts them with a stable
placeholder without requiring hosted DLP services.

#### Scenario: Known secret patterns are redacted

- **WHEN** text contains an AWS access key id, OpenAI-style `sk-` token,
  GitHub PAT prefix, PEM private key block, or long Bearer token
- **THEN** the guard replaces the secret span with a stable redaction marker
- **AND** returns a positive redaction count

#### Scenario: Clean text is unchanged

- **WHEN** text has no matching secret patterns
- **THEN** the guard returns the original text
- **AND** the redaction count is zero

### Requirement: API responses include baseline security headers

The HTTP API MUST attach baseline security headers on responses.

#### Scenario: Health response includes security headers

- **WHEN** a client requests `GET /health`
- **THEN** the response includes `X-Content-Type-Options: nosniff`
- **AND** includes `X-Frame-Options: DENY`
- **AND** includes a `Referrer-Policy` value

### Requirement: CORS is origin-scoped with explicit methods and headers

The API MUST allow only configured origins and MUST NOT use unrestricted
method/header wildcards for CORS.

#### Scenario: Allowed origin receives ACAO on preflight

- **WHEN** a browser preflight uses an origin from the configured allowlist
- **THEN** the response allows that origin

#### Scenario: Disallowed origin does not receive ACAO

- **WHEN** a browser preflight uses an origin outside the allowlist
- **THEN** the response does not allow that origin
