# provider-runtime Specification

## ADDED Requirements

### Requirement: Qwen production defaults are materialized from connected provider sync

El sistema MUST materializar defaults Qwen productivos faltantes cuando una
connection Qwen conectada sincroniza modelos conocidos, sin requerir un comando
manual adicional y sin cambiar el default fake de arranque local.

#### Scenario: Model sync configures missing Qwen defaults

- **WHEN** una connection Qwen conectada sincroniza `qwen-plus`,
  `text-embedding-v4` y `qwen3-rerank` con capabilities compatibles
- **THEN** el sistema configura `qwen-plus` como default del pool global de chat
  si el pool esta vacio
- **AND** configura `text-embedding-v4` como default de `dense_embedding` si el
  slot no tiene default existente
- **AND** configura `qwen3-rerank` como default de `rerank` si el slot no tiene
  default existente

#### Scenario: Model sync configures sparse only from native Qwen endpoint

- **WHEN** una connection Qwen sincroniza `text-embedding-v4` con capability
  `sparse_embedding`
- **AND** la connection usa DashScope native TextEmbedding como base URL
- **THEN** el sistema configura `text-embedding-v4` como default de
  `sparse_embedding` si el slot no tiene default existente
- **AND** una connection Qwen OpenAI-compatible no configura
  `sparse_embedding` automaticamente

#### Scenario: Auto defaults are idempotent and preserve user choices

- **WHEN** el sync Qwen se ejecuta mas de una vez
- **THEN** no duplica rows de catalogo, slots ni chat models
- **AND** no reemplaza defaults globales existentes
- **AND** no reemplaza un pool global de chat no vacio ni su default actual
- **AND** no guarda API keys desde environment en provider secrets

### Requirement: Qwen model catalog infers safe slot capabilities

El sistema MUST inferir capabilities seguras para modelos Qwen conocidos cuando
el provider no devuelve capabilities explicitas, evitando que modelos de chat
aparezcan como embeddings o rerank por herencia amplia de la connection.

#### Scenario: Qwen chat model is cataloged only for chat

- **WHEN** model sync descubre `qwen-plus` sin capabilities provider-explicitas
- **THEN** el catalogo lo guarda con capability `chat`
- **AND** no lo devuelve al filtrar por `dense_embedding`, `sparse_embedding`
  ni `rerank`

#### Scenario: Qwen embedding model is cataloged for dense and sparse embeddings

- **WHEN** model sync descubre `text-embedding-v4` sin capabilities
  provider-explicitas
- **THEN** el catalogo lo guarda con capabilities `dense_embedding` y
  `sparse_embedding`
- **AND** no lo devuelve al filtrar por `chat` ni `rerank`

#### Scenario: Qwen rerank model is cataloged only for rerank

- **WHEN** model sync descubre `qwen3-rerank` sin capabilities
  provider-explicitas
- **THEN** el catalogo lo guarda con capability `rerank`
- **AND** no lo devuelve al filtrar por `chat`, `dense_embedding` ni
  `sparse_embedding`

### Requirement: Provider runtime facade remains compatible after organization

El sistema MUST reorganizar el codigo interno del runtime sin romper imports
publicos usados por API, CLI, tests y callers existentes.

#### Scenario: Public provider_runtime imports still work

- **WHEN** codigo existente importa factories y errores desde
  `adaptive_rag.provider_runtime`
- **THEN** los nombres publicos siguen disponibles
- **AND** conservan el mismo comportamiento observable de resolucion fake,
  legacy `.env` y runtime settings persistidos
