# Propuesta M41 de job queue hardening

## Why

`JobRepository` ya expone `release_expired_leases` y `fail()`, pero el worker
publico de ingestion/indexing no los invoca. Un crash mid-job deja el job en
`running` eterno; errores inesperados no reintentan con backoff ni dead-letter.

## What Changes

- Worker/`run_next` llama `release_expired_leases` en cada ciclo antes de lease.
- Errores inesperados (no-block) llaman `fail()` con backoff y dead-letter real.
- Eventos `released`, `failed_attempt` y `dead_lettered` siguen visibles en
  ingestion ops list/detail.
- Test de integracion: job running con lease vencido se reencola y puede
  re-procesarse (kill mid-job / lease expiry).

## Fuera de alcance

- Multi-turn chat (M42).
- Authoring lifecycle (M43).
- CI/compose (M44).
- Redis/ARQ enterprise workers.

## Impacto

Jobs stuck en `running` se recuperan; fallas transitorias reintentan; fallas
agotadas van a dead-letter observable.
