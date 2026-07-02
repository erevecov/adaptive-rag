/**
 * @vitest-environment jsdom
 */
import { type FormEvent, useState } from 'react'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import appSource from '@/App.tsx?raw'
import { RuntimeSettingsPanel } from './RuntimeSettingsView'
import type {
  ChatRetrievalSettings,
  ProjectRuntimeSettings,
  ProviderConnection,
  ProviderConnectionCheckResponse,
  ProviderModel,
  RuntimeSlotDefault,
} from '@/lib/apiClient'
import type { RuntimeSubmodule } from './runtimeUi'

type NodeFsModule = {
  readFileSync(path: string, encoding: 'utf8'): string
}

type NodeProcess = {
  getBuiltinModule?(name: 'fs'): NodeFsModule
}

const appStyles =
  (
    globalThis as typeof globalThis & {
      process?: NodeProcess
    }
  ).process?.getBuiltinModule?.('fs').readFileSync('src/App.css', 'utf8') ??
  ''

afterEach(() => {
  cleanup()
})

const providerConnections: ProviderConnection[] = [
  {
    base_url: 'https://dashscope.example.test/compatible-mode/v1',
    capabilities: ['chat', 'dense_embedding'],
    connection_id: 'qwen-hosted',
    connection_type: 'hosted',
    created_at: '2026-06-01T00:00:00Z',
    metadata: { label: 'Qwen hosted' },
    provider: 'qwen',
    secrets: [
      {
        configured: true,
        connection_id: 'qwen-hosted',
        fingerprint: null,
        last_four: 'cret',
        secret_name: 'api_key',
        updated_at: '2026-06-01T00:00:00Z',
      },
    ],
    updated_at: '2026-06-01T00:00:00Z',
  },
  {
    base_url: 'http://localhost:8001/v1',
    capabilities: ['chat'],
    connection_id: 'local-chat',
    connection_type: 'local',
    created_at: '2026-06-01T00:00:00Z',
    metadata: null,
    provider: 'local_openai_compatible',
    secrets: [],
    updated_at: '2026-06-01T00:00:00Z',
  },
]

const providerModels: ProviderModel[] = [
  {
    capabilities: ['chat'],
    connection_id: 'qwen-hosted',
    created_at: '2026-06-01T00:00:00Z',
    last_seen_at: '2026-06-01T00:00:00Z',
    metadata: null,
    model_id: 'qwen-plus',
    pricing: null,
    updated_at: '2026-06-01T00:00:00Z',
  },
  {
    capabilities: ['dense_embedding'],
    connection_id: 'qwen-hosted',
    created_at: '2026-06-01T00:00:00Z',
    last_seen_at: '2026-06-01T00:00:00Z',
    metadata: null,
    model_id: 'text-embedding-v4',
    pricing: null,
    updated_at: '2026-06-01T00:00:00Z',
  },
]

const runtimeSlots: RuntimeSlotDefault[] = [
  {
    connection_id: 'qwen-hosted',
    created_at: '2026-06-01T00:00:00Z',
    model_id: 'qwen-plus',
    parameters: null,
    slot: 'chat',
    updated_at: '2026-06-01T00:00:00Z',
  },
]

const chatRetrievalSettings: ChatRetrievalSettings = {
  max_limit: 50,
  rerank_candidate_limit: 10,
  rerank_enabled: true,
  retrieval_limit: 5,
}

const projectRuntimeSettings: ProjectRuntimeSettings = {
  chat_models: [
    {
      connection_id: 'qwen-hosted',
      is_default: true,
      model_id: 'qwen-plus',
      parameters: null,
      source: 'global',
    },
  ],
  chat_retrieval: {
    ...chatRetrievalSettings,
    source: 'global',
  },
  project_id: '11111111-1111-4111-8111-111111111111',
  slots: [
    {
      connection_id: 'qwen-hosted',
      model_id: 'qwen-plus',
      parameters: null,
      slot: 'chat',
      source: 'global',
    },
  ],
}

function preventDefault(event: FormEvent<HTMLFormElement>) {
  event.preventDefault()
}

function renderRuntimeSettingsPanel(
  overrides: Partial<Parameters<typeof RuntimeSettingsPanel>[0]> = {},
) {
  const props: Parameters<typeof RuntimeSettingsPanel>[0] = {
    activeSubmodule: 'connections',
    chatConnectionId: 'qwen-hosted',
    chatModelId: 'qwen-plus',
    chatModels: [
      {
        connection_id: 'qwen-hosted',
        created_at: '2026-06-01T00:00:00Z',
        is_default: true,
        model_id: 'qwen-plus',
        parameters: null,
        updated_at: '2026-06-01T00:00:00Z',
      },
    ],
    chatRetrievalSettings,
    checkingConnectionId: null,
    connectionApiKey: '',
    connectionBaseUrl: '',
    connectionCapabilities: ['chat'],
    connectionCheckResults: {},
    connectionProvider: 'qwen',
    connectionType: 'hosted',
    connections: providerConnections,
    deleteConnectionConfirmation: '',
    deleteConnectionId: null,
    editingConnectionId: null,
    error: null,
    globalChatRerankCandidateLimit: 10,
    globalChatRerankEnabled: true,
    globalChatRetrievalLimit: 5,
    globalSlot: 'chat',
    globalSlotConnectionId: 'qwen-hosted',
    globalSlotModelId: 'qwen-plus',
    modelSyncConnectionId: 'qwen-hosted',
    onCancelDeleteConnection: vi.fn(),
    onCancelEditConnection: vi.fn(),
    onChatConnectionIdChange: vi.fn(),
    onChatModelIdChange: vi.fn(),
    onCheckConnection: vi.fn(),
    onConnectionApiKeyChange: vi.fn(),
    onConnectionBaseUrlChange: vi.fn(),
    onConnectionCapabilitiesChange: vi.fn(),
    onConnectionProviderChange: vi.fn(),
    onConnectionTypeChange: vi.fn(),
    onDeleteConnection: vi.fn(preventDefault),
    onDeleteConnectionConfirmationChange: vi.fn(),
    onGlobalChatRerankCandidateLimitChange: vi.fn(),
    onGlobalChatRerankEnabledChange: vi.fn(),
    onGlobalChatRetrievalLimitChange: vi.fn(),
    onGlobalSlotChange: vi.fn(),
    onGlobalSlotConnectionIdChange: vi.fn(),
    onGlobalSlotModelIdChange: vi.fn(),
    onModelSyncConnectionIdChange: vi.fn(),
    onProjectChatRerankCandidateLimitChange: vi.fn(),
    onProjectChatRerankEnabledChange: vi.fn(),
    onProjectChatRetrievalLimitChange: vi.fn(),
    onProjectSlotChange: vi.fn(),
    onProjectSlotConnectionIdChange: vi.fn(),
    onProjectSlotModelIdChange: vi.fn(),
    onRefreshGlobalDefaults: vi.fn(),
    onRefreshModelCatalog: vi.fn(),
    onRefreshProjectOverrides: vi.fn(),
    onRequestDeleteConnection: vi.fn(),
    onRequestEditConnection: vi.fn(),
    onResetProjectChatRetrieval: vi.fn(),
    onResetProjectSlot: vi.fn(),
    onSaveConnection: vi.fn(preventDefault),
    onSaveGlobalChatModel: vi.fn(preventDefault),
    onSaveGlobalChatRetrieval: vi.fn(preventDefault),
    onSaveGlobalSlot: vi.fn(preventDefault),
    onSaveProjectChatRetrieval: vi.fn(preventDefault),
    onSaveProjectOverride: vi.fn(preventDefault),
    onSyncProviderModels: vi.fn(preventDefault),
    projectChatRerankCandidateLimit: 10,
    projectChatRerankEnabled: true,
    projectChatRetrievalLimit: 5,
    projectId: '11111111-1111-4111-8111-111111111111',
    projectRuntimeSettings,
    projectSlot: 'chat',
    projectSlotConnectionId: 'qwen-hosted',
    projectSlotModelId: 'qwen-plus',
    providerModels,
    slots: runtimeSlots,
    state: 'idle',
    ...overrides,
  }

  return render(<RuntimeSettingsPanel {...props} />)
}

function StatefulDeleteRuntimePanel({
  activeSubmodule = 'connections',
}: {
  activeSubmodule?: RuntimeSubmodule
}) {
  const [deleteConnectionId, setDeleteConnectionId] = useState<string | null>(
    null,
  )
  const [deleteConnectionConfirmation, setDeleteConnectionConfirmation] =
    useState('')
  const onDeleteConnection = vi.fn(preventDefault)

  return (
    <RuntimeSettingsPanel
      activeSubmodule={activeSubmodule}
      chatConnectionId="qwen-hosted"
      chatModelId="qwen-plus"
      chatModels={[]}
      chatRetrievalSettings={chatRetrievalSettings}
      checkingConnectionId={null}
      connectionApiKey=""
      connectionBaseUrl=""
      connectionCapabilities={['chat']}
      connectionCheckResults={{}}
      connectionProvider="qwen"
      connectionType="hosted"
      connections={providerConnections}
      deleteConnectionConfirmation={deleteConnectionConfirmation}
      deleteConnectionId={deleteConnectionId}
      editingConnectionId={null}
      error={null}
      globalChatRerankCandidateLimit={10}
      globalChatRerankEnabled
      globalChatRetrievalLimit={5}
      globalSlot="chat"
      globalSlotConnectionId="qwen-hosted"
      globalSlotModelId="qwen-plus"
      modelSyncConnectionId="qwen-hosted"
      onCancelDeleteConnection={() => setDeleteConnectionId(null)}
      onCancelEditConnection={vi.fn()}
      onChatConnectionIdChange={vi.fn()}
      onChatModelIdChange={vi.fn()}
      onCheckConnection={vi.fn()}
      onConnectionApiKeyChange={vi.fn()}
      onConnectionBaseUrlChange={vi.fn()}
      onConnectionCapabilitiesChange={vi.fn()}
      onConnectionProviderChange={vi.fn()}
      onConnectionTypeChange={vi.fn()}
      onDeleteConnection={onDeleteConnection}
      onDeleteConnectionConfirmationChange={setDeleteConnectionConfirmation}
      onGlobalChatRerankCandidateLimitChange={vi.fn()}
      onGlobalChatRerankEnabledChange={vi.fn()}
      onGlobalChatRetrievalLimitChange={vi.fn()}
      onGlobalSlotChange={vi.fn()}
      onGlobalSlotConnectionIdChange={vi.fn()}
      onGlobalSlotModelIdChange={vi.fn()}
      onModelSyncConnectionIdChange={vi.fn()}
      onProjectChatRerankCandidateLimitChange={vi.fn()}
      onProjectChatRerankEnabledChange={vi.fn()}
      onProjectChatRetrievalLimitChange={vi.fn()}
      onProjectSlotChange={vi.fn()}
      onProjectSlotConnectionIdChange={vi.fn()}
      onProjectSlotModelIdChange={vi.fn()}
      onRefreshGlobalDefaults={vi.fn()}
      onRefreshModelCatalog={vi.fn()}
      onRefreshProjectOverrides={vi.fn()}
      onRequestDeleteConnection={(connectionId) => {
        setDeleteConnectionConfirmation('')
        setDeleteConnectionId(connectionId)
      }}
      onRequestEditConnection={vi.fn()}
      onResetProjectChatRetrieval={vi.fn()}
      onResetProjectSlot={vi.fn()}
      onSaveConnection={vi.fn(preventDefault)}
      onSaveGlobalChatModel={vi.fn(preventDefault)}
      onSaveGlobalChatRetrieval={vi.fn(preventDefault)}
      onSaveGlobalSlot={vi.fn(preventDefault)}
      onSaveProjectChatRetrieval={vi.fn(preventDefault)}
      onSaveProjectOverride={vi.fn(preventDefault)}
      onSyncProviderModels={vi.fn(preventDefault)}
      projectChatRerankCandidateLimit={10}
      projectChatRerankEnabled
      projectChatRetrievalLimit={5}
      projectId="11111111-1111-4111-8111-111111111111"
      projectRuntimeSettings={projectRuntimeSettings}
      projectSlot="chat"
      projectSlotConnectionId="qwen-hosted"
      projectSlotModelId="qwen-plus"
      providerModels={providerModels}
      slots={runtimeSlots}
      state="idle"
    />
  )
}

describe('RuntimeSettingsPanel', () => {
  test('does not make App import generic request state helpers from runtimeUi', () => {
    const runtimeUiImport = appSource.match(
      /from ['"]@\/features\/runtime\/runtimeUi['"]/,
    )

    expect(runtimeUiImport).toBeTruthy()
    expect(appSource).not.toMatch(
      /import\s*{[\s\S]*\b(?:RequestState|statusClassName)\b[\s\S]*}\s*from ['"]@\/features\/runtime\/runtimeUi['"]/,
    )
  })

  test('renders the selected runtime submodule panel', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
    })

    expect(
      screen.getByRole('heading', { name: 'Global defaults' }),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reload global defaults' })).toBeTruthy()
  })

  test('does not render runtime submodule segmented controls in the content panel', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
    })

    expect(
      screen.queryByRole('group', {
        name: 'Runtime submodule navigation',
      }),
    ).toBeNull()
  })

  test('keeps legacy global button CSS scoped away from UI primitives', () => {
    expect(appStyles).toContain('button:not([data-slot]) {')
    expect(appStyles).toContain('button:not([data-slot]):disabled {')
    expect(appStyles).toContain(
      ":is([data-theme='dark'], [data-theme='purple']) button:not([data-slot]) {",
    )
    expect(appStyles).toContain(
      ":is([data-theme='dark'], [data-theme='purple']) button:not([data-slot]):hover {",
    )
    expect(appStyles).not.toMatch(/(^|\n)\s*button\s*\{/)
    expect(appStyles).not.toMatch(/(^|\n)\s*button:disabled\s*\{/)
    expect(appStyles).not.toMatch(
      /:is\(\[data-theme='dark'\], \[data-theme='purple'\]\) button,/,
    )
    expect(appStyles).not.toMatch(
      /:is\(\[data-theme='dark'\], \[data-theme='purple'\]\) button:hover,/,
    )
  })

  test('wraps runtime panel headers with long status values', () => {
    const longProjectId =
      '11111111-1111-4111-8111-111111111111-project-with-long-runtime-id'
    renderRuntimeSettingsPanel({
      activeSubmodule: 'project_overrides',
      projectId: longProjectId,
    })

    const statusBadge = screen.getByText(longProjectId)
    const header = statusBadge.closest('[data-slot="panel-header"]')
    const titleGroup = screen.getByRole('heading', {
      level: 2,
      name: 'Project overrides',
    }).parentElement

    expect(header?.className).toContain('flex-col')
    expect(header?.className).toContain('sm:flex-row')
    expect(titleGroup?.className).toContain('min-w-0')
    expect(statusBadge.className).toContain('max-w-full')
    expect(statusBadge.className).toContain('break-all')
  })

  test('keeps connection form fields label-addressable without rendering secret connection controls', () => {
    renderRuntimeSettingsPanel()

    expect(screen.getByLabelText('Provider')).toBeTruthy()
    expect(screen.getByLabelText('Connection type')).toBeTruthy()
    expect(screen.getByLabelText('Base URL')).toBeTruthy()
    expect(screen.getByRole('combobox', { name: 'Capabilities' })).toBeTruthy()
    expect(screen.getByLabelText('API key')).toBeTruthy()
    expect(screen.queryByLabelText('Secret connection')).toBeNull()
  })

  test('renders connection check results with provider connection rows', () => {
    const connectionCheckResults: Record<string, ProviderConnectionCheckResponse> =
      {
        'qwen-hosted': {
          connection_id: 'qwen-hosted',
          message: 'ok',
          model_count: 2,
          ok: true,
        },
      }

    renderRuntimeSettingsPanel({ connectionCheckResults })

    const feedback = screen.getByText(
      'Connection check passed: 2 provider models reachable.',
    )

    expect(feedback.getAttribute('role')).toBe('status')
    expect(feedback.getAttribute('aria-live')).toBe('polite')
  })

  test('keeps failed connection checks as alerts', () => {
    const connectionCheckResults: Record<string, ProviderConnectionCheckResponse> =
      {
        'qwen-hosted': {
          connection_id: 'qwen-hosted',
          message: 'provider credentials rejected',
          model_count: 0,
          ok: false,
        },
      }

    renderRuntimeSettingsPanel({ connectionCheckResults })

    expect(
      screen
        .getByText('Connection check failed: provider credentials rejected')
        .getAttribute('role'),
    ).toBe('alert')
  })

  test('enables delete confirmation only for the exact connection id', async () => {
    const user = userEvent.setup()
    render(<StatefulDeleteRuntimePanel />)

    const providerConnectionsRegion = screen.getByRole('region', {
      name: 'Provider connections',
    })
    await user.click(
      within(providerConnectionsRegion).getByRole('button', {
        name: 'Delete qwen-hosted connection',
      }),
    )

    const deleteForm = screen.getByRole('form', {
      name: 'Delete qwen-hosted connection',
    })
    expect(
      within(deleteForm).getByText((_, element) => {
        return (
          element?.tagName.toLowerCase() === 'p' &&
          element.textContent === 'Type qwen-hosted to confirm deletion.'
        )
      }),
    ).toBeTruthy()
    const confirmation = screen.getByLabelText(
      'Confirm connection ID',
    ) as HTMLInputElement
    const deleteButton = screen.getByRole('button', {
      name: 'Delete connection',
    }) as HTMLButtonElement

    expect(deleteButton.disabled).toBe(true)
    await user.type(confirmation, 'wrong-id')
    expect(deleteButton.disabled).toBe(true)
    await user.clear(confirmation)
    await user.type(confirmation, 'qwen-hosted')
    expect(deleteButton.disabled).toBe(false)
  })
})
