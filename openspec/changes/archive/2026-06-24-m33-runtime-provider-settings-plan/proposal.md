# Proposal M33 runtime provider settings plan

## Why

Adaptive RAG ya tiene provider runtime live opt-in, pero la configuracion vive
principalmente en `.env`: provider/modelo por operacion, Qwen API key/base URL,
timeouts, retries y presupuestos. Ese modelo fue suficiente para smokes live y
evals hosted, pero queda corto para una app local-first con UI:

- El usuario no deberia editar `.env` para rotar o probar una API key.
- El frontend no debe ver ni guardar secrets.
- Los proyectos deben aislar conocimiento, chats y settings propias, pero la
  configuracion de providers debe ser global del workspace local.
- Hosted providers y conexiones locales deben poder coexistir al mismo tiempo.
- Cada caso de uso LLM necesita un slot claro: chat, embeddings, rerank y
  contextualization pueden usar providers/modelos distintos.
- El slot de chat necesita un pool de modelos habilitados, con un default, para
  permitir seleccion futura sin hacer los slots dinamicos.

M33 abre un plan para convertir el runtime de providers en configuracion
persistida y operable, inspirada en el patron global de `model_settings` y
`chat_allowed_models`, pero adaptada a Adaptive RAG porque aqui
si existen proyectos y overrides por proyecto.

## What Changes

- Agregar el change OpenSpec `m33-runtime-provider-settings-plan`.
- Definir connections globales de provider para hosted, local y fake.
- Definir secrets globales cifrados y nunca retornados al frontend.
- Mantener `.env` como fallback local/legacy, no como unica fuente de verdad.
- Definir slots fijos iniciales:
  - `chat`
  - `dense_embedding`
  - `sparse_embedding`
  - `rerank`
  - `contextualization`
- Definir defaults globales por slot.
- Definir un pool global de modelos de chat con exactamente un default.
- Definir overrides por proyecto para slots individuales y para el pool/default
  de chat cuando un proyecto lo requiera.
- Definir resolucion deterministica:
  `project override` > `global default` > `.env`/fake fallback.
- Definir una superficie frontend de runtime settings sin exponer secrets.
- Planear slices de implementacion secuenciales para evitar mezclar schema,
  API, runtime y UI en un PR grande.

## Out of Scope

- No implementar runtime, migrations, API ni frontend en este PR de plan.
- No agregar slots dinamicos; el conjunto inicial es fijo y se ajustara por
  OpenSpec cuando el producto lo necesite.
- No administrar procesos locales de modelos, descargas ni lifecycle de Ollama,
  llama.cpp u otros runtimes.
- No promocionar providers live como default obligatorio.
- No cambiar `dense` como default de retrieval del producto.
- No agregar auth multi-user ni separacion de secrets por usuario.
- No devolver API keys, tokens ni secrets cifrados por API o frontend.
- No agregar nuevos providers hosted fuera de los ya definidos por un slice
  especifico.

## Validation

- Validar `m33-runtime-provider-settings-plan` con OpenSpec strict.
- Validar specs canonicas con OpenSpec strict.
- Revisar diff hygiene.
- La implementacion futura debe preservar tests offline sin red ni credenciales.
