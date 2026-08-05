import { describe, expect, test } from 'vitest'

import type { ProviderConnection } from '@/lib/apiClient'

import {
  connectionOptionLabel,
  connectionTypeLabel,
  missingSyncedModelMessage,
  providerLabel,
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
    expect(providerLabel('fake')).toBe('Fake')
    expect(connectionTypeLabel('hosted')).toBe('Hosted')
    expect(
      missingSyncedModelMessage({
        connectionId: 'qwen-hosted',
        modelOptions: [],
        target: 'dense_embedding',
      }),
    ).toBe('Sync models for qwen-hosted before saving Dense Embedding.')
  })
})
