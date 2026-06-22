# Qwen local model options

Snapshot verificado: 2026-06-22.

Este documento guarda la decision preliminar sobre modelos Qwen levantables en
local para Adaptive RAG. No es un contrato de implementacion: cualquier cambio
ejecutable en providers, defaults, storage o API debe pasar por un change
OpenSpec.

## Contexto del repo

- `provider_runtime` ya modela Qwen como provider live opt-in con
  `ADAPTIVE_RAG_QWEN_API_KEY` y `ADAPTIVE_RAG_QWEN_BASE_URL`.
- Chat Qwen espera un endpoint OpenAI-compatible `/chat/completions` con tool
  calling y usa la tool `retrieval_search`.
- Dense embeddings usan `EMBEDDING_DIMENSIONS = 1024`, persistidos en pgvector.
- Rerank Qwen espera la forma Qwen/DashScope: endpoint `/reranks` o
  `services/rerank/text-rerank/text-rerank` y respuesta `output.results`.
- Sparse ya existe como modo experimental `dense_sparse`, pero no hay provider
  sparse productivo implementado.

## Matriz de capacidades

| Capacidad | Local Qwen | Candidato | Nota de integracion | Estado |
| --- | --- | --- | --- | --- |
| Chat + tool calling | Si | `Qwen3-*` instruct, por ejemplo `Qwen3-8B` | Se puede servir con `vLLM` como endpoint OpenAI-compatible. Calza con el runner actual. | Candidato listo |
| Routing | Si | `Qwen3` instruct chico | No requiere un modelo router dedicado; usar structured output o tool choice sobre un modelo pequeno. | Candidato listo |
| Dense embedding | Si | `Qwen3-Embedding-0.6B` primero; escalar a `4B/8B` si hace falta | La variante 0.6B puede producir 1024 dimensiones, compatible con el schema actual. Requiere endpoint local o wrapper compatible con `/embeddings`. | Candidato listo |
| Reranking | Si, con wrapper | `Qwen3-Reranker-0.6B` primero; escalar a `4B/8B` si hace falta | El modelo local existe, pero el repo espera shape Qwen/DashScope `output.results`; no es drop-in salvo que se exponga un wrapper compatible. | Candidato con trabajo |
| Sparse retrieval | No confirmado como open local Qwen | DashScope `text-embedding-v4` tiene sparse/dense&sparse hosted | No se encontro un sparse encoder Qwen open-weight local equivalente. Mantener Qwen sparse en hold; si sparse local es prioridad, evaluar BM25/SPLADE/BGE-M3 u otro provider no-Qwen. | Hold |
| STT | Si | `Qwen3-ASR-0.6B` o `Qwen3-ASR-1.7B` | Encaja como servicio local audio -> texto antes del pipeline RAG. | Candidato listo |
| TTS | Si, con wrapper | `Qwen3-TTS-0.6B` o `Qwen3-TTS-1.7B` | Encaja como servicio local texto -> audio despues del answer. Requiere adapter/wrapper de audio. | Candidato con trabajo |
| Voz end-to-end | Si, pesado | `Qwen3-Omni-30B-A3B` | Puede manejar audio in/out local, pero aumenta blast radius y reduce observabilidad fina frente a sandwich STT -> RAG -> TTS. | Hold para v1 |

## Recomendacion

Para una ruta local-first pragmatica:

1. STT: `Qwen3-ASR-0.6B`.
2. Chat/routing: `Qwen3` instruct servido por `vLLM` con API OpenAI-compatible.
3. Dense embeddings: `Qwen3-Embedding-0.6B`, manteniendo 1024 dimensiones.
4. Rerank: `Qwen3-Reranker-0.6B` detras de un wrapper compatible con el
   contrato actual de `QwenHTTPRerankClient`.
5. TTS: `Qwen3-TTS-0.6B`.

La opcion recomendada para voz es sandwich STT -> texto RAG -> TTS, no
`Qwen3-Omni` end-to-end, porque preserva audit trail, citations, provider usage
y fallbacks por etapa. `Qwen3-Omni` queda como alternativa posterior para
experimentos de voz multimodal cuando haya capacidad GPU y criterios de eval.

Sparse debe permanecer en hold para Qwen local. DashScope documenta sparse
hosted, pero una implementacion local-only necesita evidencia nueva o aceptar
un provider sparse no-Qwen por diseno.

## Fuentes verificadas

- [Qwen vLLM deployment](https://qwen.readthedocs.io/en/latest/deployment/vllm.html)
- [Qwen function calling](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
- [Qwen3-Embedding and Qwen3-Reranker](https://github.com/QwenLM/Qwen3-Embedding)
- [Alibaba Cloud embedding models, including sparse hosted mode](https://www.alibabacloud.com/help/en/model-studio/embedding)
- [Qwen3-ASR](https://github.com/QwenLM/Qwen3-ASR)
- [Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS)
- [Qwen3-Omni](https://github.com/QwenLM/Qwen3-Omni)
