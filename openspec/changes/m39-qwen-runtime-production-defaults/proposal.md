# Proposal M39 Qwen runtime production defaults

## Why

Runtime settings ya permite conexiones globales, catalogo de modelos, slots
fijos, pool de chat y overrides por proyecto. El estado actual todavia deja
dos fricciones para usar Qwen en un entorno productivo:

- `adaptive_rag.provider_runtime` concentra resolucion, secrets, fallback de
  `.env`, factories y wiring de clientes live en un modulo grande.
- Configurar Qwen requiere pasos manuales de connection, catalogo, slots y pool
  de chat; los IDs correctos de modelos existen en tests/docs pero conectar el
  provider no materializa defaults faltantes automaticamente.

Ademas, el sync de modelos puede heredar capabilities amplias de la connection
cuando el provider no devuelve capabilities por modelo. Eso es comodo para UI,
pero demasiado laxo para production: `qwen-plus` no debe aparecer como embedding
solo porque la connection declara varias capabilities.

## What Changes

- Agregar materializacion automatica e idempotente de Qwen production defaults
  cuando el provider Qwen queda conectado y sincroniza su catalogo de modelos.
- Configurar por defecto los modelos Qwen actuales del repo:
  - `chat`: `qwen-plus`
  - `dense_embedding`: `text-embedding-v4`
  - `sparse_embedding`: `text-embedding-v4`
  - `rerank`: `qwen3-rerank`
- Separar endpoints cuando corresponde:
  - chat usa OpenAI-compatible `/compatible-mode/v1`.
  - dense embedding puede usar OpenAI-compatible o DashScope native.
  - sparse embedding usa DashScope native TextEmbedding.
  - rerank usa DashScope rerank endpoint derivado desde base compatible o native.
- Clasificar capabilities conocidas por modelo Qwen durante model sync para no
  marcar modelos incompatibles como disponibles para slots incorrectos.
- Reorganizar el runtime en modulos enfocados manteniendo compatibilidad de
  imports publicos desde `adaptive_rag.provider_runtime`.
- Agregar cobertura API/model-sync que valide resolucion efectiva sin exponer
  secrets ni llamar red fuera del sync iniciado por el usuario.

## Out of Scope

- No activar Qwen automaticamente al arrancar API/CLI sin una connection Qwen
  conectada y sincronizada.
- No sobrescribir defaults globales ni pool de chat que el usuario ya haya
  configurado.
- No guardar API keys desde environment en la base de datos.
- No eliminar fallback legacy de `.env`.
- No cambiar el default fake de tests/CI ni el acceptance local obligatorio.
- No agregar nuevos providers ni nuevos slots dinamicos.
- No cambiar precios por defecto si el provider no devuelve pricing.

## Validation

- OpenSpec strict para el nuevo change.
- Tests unitarios para defaults Qwen, materializacion idempotente y capability
  inference.
- Tests de runtime resolution para que los slots Qwen resuelvan modelos
  correctos y secrets se mantengan redacted.
- Tests API focalizados para model sync production-ready.
- Suite backend relevante, ruff, mypy y `git diff --check`.
