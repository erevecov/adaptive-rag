# Diseno M2 de URL fetch policy

## Contexto

La cola de jobs permite coordinar ingestion, pero la descarga de URLs debe tener una frontera de seguridad antes de ejecutar workers reales. El primer consumidor sera futuro ingestion, no endpoints publicos.

## Objetivos

- Proveer una API pequena para validar URLs y descargar contenido con politica.
- Bloquear esquemas no HTTP(S), credenciales en URL, hosts sin DNS valido e IPs no globales.
- Validar cada redirect manualmente antes de seguirlo.
- Enforzar allowlist de content types y `max_response_bytes` tanto por `Content-Length` como por conteo de stream.
- Mantener tests sin red real usando resolver y stream factory inyectables.

## No objetivos

- No implementar worker loop.
- No parsear HTML ni PDFs.
- No guardar documents, sources o chunks.
- No crear politicas por proyecto todavia.
- No resolver pinning de socket a IP; este change valida DNS antes de cada request y redirect.

## Decisiones

### D1. Policy como dataclass inmutable

`URLFetchPolicy` define `max_response_bytes`, `max_redirects`, timeout y allowlists. Esto mantiene defaults auditables y facil de testear sin settings globales.

### D2. Resolver inyectable

El fetcher recibe un resolver de DNS para tests y futuras adaptaciones. La implementacion default usa `socket.getaddrinfo`.

### D3. Redirects manuales

HTTPX se usa con `follow_redirects=False`. Cada `Location` se normaliza con `urljoin`, se valida y solo despues se solicita.

### D4. Stream con limite incremental

El fetcher usa streaming HTTPX (`iter_bytes`) para no cargar respuestas completas antes de verificar tamano.

## Riesgos y mitigaciones

- Riesgo: DNS puede cambiar entre validacion y conexion. Mitigacion: este slice valida antes de cada request y redirect; pinning de socket queda fuera de alcance para v1 local.
- Riesgo: allowlist demasiado estrecha. Mitigacion: defaults cubren HTML, XHTML, plain text y PDF; el caller puede pasar otra policy.
- Riesgo: tests con red real sean fragiles. Mitigacion: tests usan stream factory y resolver fake.

## Despliegue

1. Agregar OpenSpec change.
2. Escribir tests rojos de policy y fetcher.
3. Implementar modulo `adaptive_rag.ingestion.url_fetch_policy`.
4. Validar quality gate y archivar el change.

