# Tareas M2 de URL fetch policy

## 1. Planificacion y setup

- [x] 1.1 Confirmar merge de `m2-job-queue` en `origin/main`.
- [x] 1.2 Crear branch `codex/m2-url-fetch-policy` desde el `origin/main` actual.
- [x] 1.3 Ejecutar baseline: `uv run pytest`, `uv run ruff check .`, `uv run mypy src`, `openspec validate --specs --strict`.
- [x] 1.4 Consultar docs actuales de HTTPX con Context7 para streaming/redirect behavior.

## 2. Contrato OpenSpec

- [x] 2.1 Agregar propuesta, diseno, tasks y delta spec para `m2-url-fetch-policy`.
- [x] 2.2 Validar `openspec validate m2-url-fetch-policy --strict`.

## 3. Tests TDD

- [x] 3.1 Agregar tests rojos para validar URLs permitidas y bloqueadas.
- [x] 3.2 Agregar tests rojos para redirects seguros e inseguros.
- [x] 3.3 Agregar tests rojos para content type y tamano maximo.
- [x] 3.4 Agregar tests rojos para streaming sin red real.

## 4. Implementacion

- [x] 4.1 Crear paquete `adaptive_rag.ingestion`.
- [x] 4.2 Implementar `URLFetchPolicy`, errores tipados y `URLFetcher`.
- [x] 4.3 Exportar API publica del paquete.

## 5. Quality gate y handoff

- [x] 5.1 Ejecutar `uv run pytest`.
- [x] 5.2 Ejecutar `uv run ruff check .`.
- [x] 5.3 Ejecutar `uv run mypy src`.
- [x] 5.4 Ejecutar `openspec validate --specs --strict`.
- [x] 5.5 Archivar `m2-url-fetch-policy` y actualizar docs de progreso.
