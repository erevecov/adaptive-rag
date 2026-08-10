import { describe, expect, test } from 'vitest'

import type { ProviderConnection } from '@/lib/apiClient'

import {
  RUNTIME_SLOTS,
  connectionOptionLabel,
  connectionTypeLabel,
  formatProviderModelPricing,
  missingSyncedModelMessage,
  providerLabel,
  qwenServiceModelEndpointWarning,
  slotLabel,
} from './runtimeUi'

const baseConnection: ProviderConnection = {
  base_url: null,
  capabilities: ['chat'],
  connection_id: 'qwen-hosted',
  connection_type: 'hosted',
  created_at: '2026-01-01T00:00:00Z',
  metadata: null,
  provider: 'qwen',
  secrets: [],
  updated_at: '2026-01-01T00:00:00Z',
}

describe('runtimeUi labels', () => {
  test('Title Cases connection option provider and type', () => {
    expect(connectionOptionLabel(baseConnection)).toBe(
      'qwen-hosted (Qwen/Hosted)',
    )
    expect(
      connectionOptionLabel({
        ...baseConnection,
        connection_id: 'local-chat',
        connection_type: 'local',
        metadata: { label: 'Local chat' },
        provider: 'local_openai_compatible',
      }),
    ).toBe('Local chat (Local OpenAI-compatible/Local)')
  })

  test('maps known slot and provider tokens', () => {
    expect(slotLabel('dense_embedding')).toBe('Dense Embedding')
    expect(slotLabel('chat')).toBe('Chat')
    expect(slotLabel('vision')).toBe('Vision')
    expect(RUNTIME_SLOTS).toContain('vision')
    expect(providerLabel('fake')).toBe('Fake')
    expect(connectionTypeLabel('hosted')).toBe('Hosted')
    expect(
      missingSyncedModelMessage({
        connectionId: 'qwen-hosted',
        modelOptions: [],
        target: 'dense_embedding',
      }),
    ).toBe(
      'No Dense Embedding models in the catalog for this connection. ' +
        'Open Model Catalog to sync, or pick a connection that exposes Dense Embedding models.',
    )
  })
})

describe('qwenServiceModelEndpointWarning', () => {
  test('warns for rerank/embed on Bailian Token Plan compatible-mode URL', () => {
    const baseUrl =
      'https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1'
    expect(
      qwenServiceModelEndpointWarning({
        provider: 'qwen',
        baseUrl,
        capabilities: ['rerank'],
      }),
    ).toMatch(/DashScope|404/i)
    expect(
      qwenServiceModelEndpointWarning({
        provider: 'qwen',
        baseUrl,
        capabilities: ['dense_embedding'],
      }),
    ).toMatch(/embedding/i)
    expect(
      qwenServiceModelEndpointWarning({
        provider: 'qwen',
        baseUrl,
        capabilities: ['sparse_embedding'],
      }),
    ).toMatch(/Sparse embeddings/i)
  })

  test('is silent for chat and for native DashScope service URLs', () => {
    expect(
      qwenServiceModelEndpointWarning({
        provider: 'qwen',
        baseUrl:
          'https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1',
        capabilities: ['chat'],
      }),
    ).toBeNull()
    expect(
      qwenServiceModelEndpointWarning({
        provider: 'qwen',
        baseUrl: 'https://dashscope-intl.aliyuncs.com/api/v1',
        capabilities: ['rerank'],
      }),
    ).toBeNull()
    expect(
      qwenServiceModelEndpointWarning({
        provider: 'qwen',
        baseUrl:
          'https://dashscope-intl.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding',
        capabilities: ['dense_embedding', 'sparse_embedding'],
      }),
    ).toBeNull()
  })
})

describe('formatProviderModelPricing', () => {
  test('formats chat list prices with optional thinking tier', () => {
    expect(
      formatProviderModelPricing({
        input_per_million_tokens_usd: 0.4,
        output_per_million_tokens_usd: 1.2,
        output_thinking_per_million_tokens_usd: 4,
        currency: 'USD',
        source: 'alibaba_model_studio_singapore_list',
      }),
    ).toEqual({
      hasPricing: true,
      summary: 'In $0.40 · Out $1.20 · Think $4.00 /1M',
      badgeLabel: 'Priced',
    })
  })

  test('formats embedding/rerank input-only prices', () => {
    expect(
      formatProviderModelPricing({
        input_per_million_tokens_usd: 0.07,
        currency: 'USD',
      }),
    ).toEqual({
      hasPricing: true,
      summary: 'In $0.07 /1M',
      badgeLabel: 'Priced',
    })
  })

  test('returns No pricing for null empty or unknown shapes', () => {
    expect(formatProviderModelPricing(null)).toEqual({
      hasPricing: false,
      summary: null,
      badgeLabel: 'No pricing',
    })
    expect(formatProviderModelPricing({})).toEqual({
      hasPricing: false,
      summary: null,
      badgeLabel: 'No pricing',
    })
    expect(
      formatProviderModelPricing({ notes: 'Billed by input tokens' }),
    ).toEqual({
      hasPricing: false,
      summary: null,
      badgeLabel: 'No pricing',
    })
  })

  test('accepts numeric strings without inventing values', () => {
    expect(
      formatProviderModelPricing({
        input_per_million_tokens_usd: '0.1',
        output_per_million_tokens_usd: '0.4',
      }),
    ).toEqual({
      hasPricing: true,
      summary: 'In $0.10 · Out $0.40 /1M',
      badgeLabel: 'Priced',
    })
  })

  test('formats image and character billing units', () => {
    expect(
      formatProviderModelPricing({
        usd_per_image: 0.03,
        currency: 'USD',
      }),
    ).toEqual({
      hasPricing: true,
      summary: '$0.03 /image',
      badgeLabel: 'Priced',
    })
    expect(
      formatProviderModelPricing({
        input_per_10k_characters_usd: 0.2,
        currency: 'USD',
      }),
    ).toEqual({
      hasPricing: true,
      summary: '$0.20 /10k chars',
      badgeLabel: 'Priced',
    })
  })
})
