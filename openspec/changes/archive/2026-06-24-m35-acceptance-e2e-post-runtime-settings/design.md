# Design M35 acceptance e2e post runtime settings

## Runtime acceptance shape

M35 agrega un comando publico `adaptive-rag acceptance runtime-settings-smoke`.
El comando crea una configuracion fake autocontenida en la base local:
provider connection global, catalogo de modelos fake, defaults globales para
`chat`, `dense_embedding` y `contextualization`, y un override de proyecto para
`dense_embedding`.

El smoke no depende de red ni de secrets. Qwen/local live quedan fuera del gate
default porque la meta es probar que la resolucion persistida funciona en el
producto local. El reporte mantiene espacio para indicar esos sistemas como
opt-in.

## Data flow

1. Crear/sincronizar provider connection fake con capabilities requeridas.
2. Persistir el catalogo fake mediante `ProviderModelCatalogRepository`.
3. Setear defaults globales con `RuntimeSettingsRepository`.
4. Crear project/source e ingestion usando el flujo first-run equivalente.
5. Crear override por proyecto para `dense_embedding`.
6. Resolver provider/chat runner desde `provider_runtime` con `session` y
   `project_id`.
7. Ejecutar chunking, contextualization, dense embeddings y chat citado.
8. Serializar criterios y evidencias sin secrets.

## Error handling

El comando debe fallar con exit code `1` si ingestion no procesa, si el catalogo
no queda disponible, si la resolucion efectiva no hereda/overridea lo esperado o
si chat no devuelve citations. El mensaje stderr debe ser estable y venir de una
exception de acceptance.

## Testing

El primer test debe fallar porque el comando no existe. Luego se implementa el
comando y el runner minimo. La prueba principal valida JSON, criterios pasados,
catalogo fake, sources de runtime settings (`inherited`/`overridden`) y ausencia
del valor secreto sentinel en el payload.
