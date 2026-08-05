# Propuesta Bloque C — User memory minima

## Why

Anti-roadmap: memory UI without durable storage is forbidden. Ship table +
API + approval + chat injection first.

## What Changes

- `user_memories` table (proposed/approved/rejected)
- Service propose/approve/reject/list + injection text
- API under `/users/me/memories`
- Chat injects approved memories when user_id present
- OpenSpec + tests

## Fuera de alcance

- Memory management UI
- Automatic learning from chat without proposal
- Cross-tenant sharing
