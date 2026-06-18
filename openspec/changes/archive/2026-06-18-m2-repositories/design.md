# Diseno M2 de repositories

## Contexto

M2 ya fijo el schema relacional para proyectos, sources, documents, document_versions, chunks y sparse embeddings. El siguiente riesgo es que features posteriores consulten tablas directamente y olviden el filtro de proyecto.

## Objetivos

- Proveer una API pequena de repositories para operaciones CRUD iniciales del dominio.
- Centralizar `project_id` como filtro obligatorio para lecturas de sources, documents y chunks.
- Mantener filtros de metadata acotados a columnas ya modeladas: `source_type`, `external_id`, `tags`, `source_id`, `stable_id`, `created_at`.
- Devolver modelos SQLAlchemy existentes sin introducir DTOs prematuros.
- Mantener los repositories sin ownership transaccional: el caller controla `commit()` y `rollback()`.

## No objetivos

- No resolver ingestion completa.
- No implementar ranking ni busqueda vectorial.
- No agregar filtros arbitrarios sobre JSON profundo.
- No crear Unit of Work ni abstracciones async.
- No cambiar modelos ni migraciones existentes salvo que un test revele un defecto directo.

## Decisiones

### D1. Session inyectada

Cada repository recibe una `sqlalchemy.orm.Session`. Esto mantiene compatibilidad con `session_scope()` y evita crear un contenedor de dependencias antes de que existan endpoints reales.

### D2. Project id explicito

Los metodos que leen o buscan datos de proyecto exigen `project_id` como argumento. Aunque algunas tablas tengan relaciones indirectas, el filtro debe estar visible en el metodo para que el contrato sea revisable.

### D3. Filtros tipados antes que DSL generico

Sources y documents usan dataclasses de filtros con campos conocidos. Un DSL generico de metadata seria prematuro y haria mas dificil auditar que columnas e indices se usan.

### D4. Commit externo

Los repositories llaman `session.add()` y `session.flush()` cuando necesitan IDs, pero no hacen `commit()`. Esto permite componer operaciones de ingestion en una sola transaccion en changes posteriores.

## Riesgos y mitigaciones

- Riesgo: duplicar reglas de integridad que ya viven en DB. Mitigacion: los repositories no reimplementan uniqueness; dejan que constraints fallen y los tests cubren el comportamiento observable.
- Riesgo: filtros JSON varian entre SQLite y Postgres. Mitigacion: `tags` usa igualdad/contiene simple en el contrato unitario; filtros JSON profundos quedan fuera de alcance.
- Riesgo: la API crece demasiado. Mitigacion: solo se agregan metodos requeridos por el schema actual y por los proximos slices de ingestion/retrieval.

## Despliegue

1. Agregar tests rojos de repository con SQLite in-memory.
2. Implementar repositories sincronicos y filtros tipados.
3. Validar con `uv run pytest`, `uv run ruff check .`, `uv run mypy src` y `openspec validate --specs --strict`.
4. Mantener `m2-job-queue` como siguiente tarea despues de cerrar este slice.

