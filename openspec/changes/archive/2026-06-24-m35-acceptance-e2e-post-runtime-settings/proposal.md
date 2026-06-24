# Proposal M35 acceptance e2e post runtime settings

## Why

M33 y M34 cerraron la configuracion runtime global: provider connections,
secrets cifrados, slots fijos, pool/default de chat, overrides por proyecto y
catalogo de modelos. El siguiente riesgo no es otra feature, sino que el flujo
producto completo use esas settings efectivas de punta a punta.

El gate actual `adaptive-rag v1 quality-gate` prueba authoring, ingestion,
indexing y chat con providers inyectados desde el CLI, pero no demuestra que una
instalacion pueda configurar runtime settings persistidos, sincronizar modelos,
resolver defaults/overrides por proyecto y ejecutar chat citado con esa
resolucion.

## What Changes

- Agregar un smoke de acceptance publico para runtime settings post-M34.
- Reutilizar el flujo local-first fake por defecto, sin Qwen live obligatorio.
- Configurar provider connections globales, sincronizar catalogo fake, setear
  slots globales y un override por proyecto.
- Resolver providers efectivos desde DB para ejecutar ingestion, embeddings y
  chat citado.
- Emitir reporte JSON machine-readable con criterios, catalogo, settings
  efectivas y evidencia de first-run.
- Documentar que Qwen/local live siguen opt-in para acceptance manual posterior.

## Out of Scope

- No llamar Qwen live en el gate default.
- No crear otro frontend flow ni screenshots en este slice.
- No cambiar defaults de retrieval.
- No reemplazar `adaptive-rag v1 quality-gate`; este smoke complementa el gate
  post-runtime-settings.
- No exponer ni serializar secrets.

## Validation

- TDD sobre CLI acceptance.
- Tests unitarios del reporte si hace falta separar serializacion.
- OpenSpec strict.
- Backend quality gate.
