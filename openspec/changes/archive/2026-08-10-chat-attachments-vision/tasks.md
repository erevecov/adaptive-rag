# Tasks — Chat attachments + vision model path

Spec vinculante: `design.md` (mismo directorio). Orden secuencial.

## Task 1: DB — modelo + migracion + repositorio

- `ChatAttachment` (design §2), migracion con `down_revision="j9k0l1m2n3o4"`,
  `ChatAttachmentRepository`, exports en `__init__.py`.
- Tests unit del repositorio (design §7).
- Verificacion: `uv run pytest tests/unit/db -q`, `uv run ruff check .`,
  `uv run mypy src`. Migracion: `uv run alembic upgrade head` contra SQLite
  local o verificar con `alembic history`/`upgrade --sql` si no hay DB.

## Task 2: API upload/delete/get + schemas

- Router + endpoints (design §3), `python-multipart` en pyproject + lock.
- Tests integration (design §7, bloque API).
- Verificacion: `uv run pytest tests/integration/api/test_chat_attachments.py -q`,
  ruff, mypy.

## Task 3: Chat service + runner multimodal + capabilities + vision slot

- `chat/attachments.py`, cambios en schemas/models/service/qwen/runners/
  qwen_defaults y factories (design §4-5), metadata refs en mensaje usuario.
- Vision slot end-to-end (design §5b): constante + constraints + migracion +
  resolucion + factories/DI + `runtimeUi.ts` (label Vision) en FE.
- Tests (design §7, bloques chat path y vision slot).
- Verificacion: `uv run pytest tests/unit/chat tests/unit/runtime
  tests/integration/api -q`, ruff, mypy; `cd frontend && pnpm exec vitest run
  src/features/runtime` y `pnpm typecheck`.

## Task 4: Frontend composer + apiClient + transcript

- Todo design §6 con sus tests vitest.
- Verificacion: `cd frontend && pnpm exec vitest run` (al menos los archivos
  nuevos/tocados) y `pnpm typecheck`.

## Task 5: Cierre (controller)

- Suite completa backend + frontend, ruff, mypy, typecheck.
- Review final cruzada; reporte de archivos y como probar en local.
