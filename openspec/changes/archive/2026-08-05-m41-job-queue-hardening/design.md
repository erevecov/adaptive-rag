# Diseno M41 — job queue hardening

## Decisiones

1. **Lease recovery en cada `run_next`:** antes de `lease_next`, llamar
   `release_expired_leases(project_id, now)` para el proyecto. Barato y
   evita jobs `running` eternos tras kill de worker.

2. **Block vs fail:**
   - Errores de dominio no retryables (`IngestionPipelineError`,
     `IndexingPipelineError`, `URLFetchPolicyError`, etc.) siguen en `block()`.
   - Cualquier otra excepcion inesperada → `fail()` con
     `retry_after = now + backoff(attempts)` y mensaje en `last_error`.

3. **Backoff:** `min(60, 2 ** (attempts - 1))` segundos (1, 2, 4, 8, …, 60).
   Simple y determinista para tests.

4. **Observabilidad:** eventos existentes del repository bastan
   (`released`, `failed_attempt`, `dead_lettered`); no nuevos event types.

## Alternativas rechazadas

- Heartbeat de lease mid-job: mas complejo; M41 solo recovery por expiry.
- Fail global sin block: rompe contrato actual de errores de source invalidos.
