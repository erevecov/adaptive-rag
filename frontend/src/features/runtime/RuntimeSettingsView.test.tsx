/**
 * @vitest-environment jsdom
 */
import { type FormEvent, useState } from 'react'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import appSource from '@/App.tsx?raw'
import runtimeSource from './RuntimeSettingsView.tsx?raw'
import {
  ProviderModelCatalogView,
  RuntimeSettingsPanel,
} from './RuntimeSettingsView'
import { installPointerEventMocks } from '@/test/pointerEvents'
import type {
  ChatRetrievalSettings,
  WorkspaceRuntimeSettings,
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

installPointerEventMocks()

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

const pricedProviderModels: ProviderModel[] = [
  {
    capabilities: ['chat'],
    connection_id: 'qwen-hosted',
    created_at: '2026-06-01T00:00:00Z',
    last_seen_at: '2026-06-01T00:00:00Z',
    metadata: null,
    model_id: 'qwen-plus',
    pricing: {
      input_per_million_tokens_usd: 0.4,
      output_per_million_tokens_usd: 1.2,
      output_thinking_per_million_tokens_usd: 4,
      currency: 'USD',
      source: 'alibaba_model_studio_singapore_list',
    },
    updated_at: '2026-06-01T00:00:00Z',
  },
  {
    capabilities: ['dense_embedding', 'sparse_embedding'],
    connection_id: 'qwen-hosted',
    created_at: '2026-06-01T00:00:00Z',
    last_seen_at: '2026-06-01T00:00:00Z',
    metadata: null,
    model_id: 'text-embedding-v4',
    pricing: {
      input_per_million_tokens_usd: 0.07,
      currency: 'USD',
    },
    updated_at: '2026-06-01T00:00:00Z',
  },
  {
    capabilities: ['rerank'],
    connection_id: 'qwen-hosted',
    created_at: '2026-06-01T00:00:00Z',
    last_seen_at: '2026-06-01T00:00:00Z',
    metadata: null,
    model_id: 'experimental-preview',
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

const workspaceRuntimeSettings: WorkspaceRuntimeSettings = {
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
  workspace_id: '11111111-1111-4111-8111-111111111111',
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
    isCreatingConnection: false,
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
    onWorkspaceChatRerankCandidateLimitChange: vi.fn(),
    onWorkspaceChatRerankEnabledChange: vi.fn(),
    onWorkspaceChatRetrievalLimitChange: vi.fn(),
    onWorkspaceSlotChange: vi.fn(),
    onWorkspaceSlotConnectionIdChange: vi.fn(),
    onWorkspaceSlotModelIdChange: vi.fn(),
    onRefreshWorkspaceOverrides: vi.fn(),
    onRequestCreateConnection: vi.fn(),
    onRequestDeleteConnection: vi.fn(),
    onRequestEditConnection: vi.fn(),
    onResetWorkspaceChatRetrieval: vi.fn(),
    onResetWorkspaceSlot: vi.fn(),
    onSaveConnection: vi.fn(preventDefault),
    onSaveGlobalChatModel: vi.fn(preventDefault),
    onSaveGlobalChatRetrieval: vi.fn(preventDefault),
    onSaveGlobalSlot: vi.fn(preventDefault),
    onSaveWorkspaceChatRetrieval: vi.fn(preventDefault),
    onSaveWorkspaceOverride: vi.fn(preventDefault),
    workspaceChatRerankCandidateLimit: 10,
    workspaceChatRerankEnabled: true,
    workspaceChatRetrievalLimit: 5,
    workspaceId: '11111111-1111-4111-8111-111111111111',
    workspaceRuntimeSettings,
    workspaceSlot: 'chat',
    workspaceSlotConnectionId: 'qwen-hosted',
    workspaceSlotModelId: 'qwen-plus',
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
      isCreatingConnection={false}
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
      onWorkspaceChatRerankCandidateLimitChange={vi.fn()}
      onWorkspaceChatRerankEnabledChange={vi.fn()}
      onWorkspaceChatRetrievalLimitChange={vi.fn()}
      onWorkspaceSlotChange={vi.fn()}
      onWorkspaceSlotConnectionIdChange={vi.fn()}
      onWorkspaceSlotModelIdChange={vi.fn()}
      onRefreshWorkspaceOverrides={vi.fn()}
      onRequestCreateConnection={vi.fn()}
      onRequestDeleteConnection={(connectionId) => {
        setDeleteConnectionConfirmation('')
        setDeleteConnectionId(connectionId)
      }}
      onRequestEditConnection={vi.fn()}
      onResetWorkspaceChatRetrieval={vi.fn()}
      onResetWorkspaceSlot={vi.fn()}
      onSaveConnection={vi.fn(preventDefault)}
      onSaveGlobalChatModel={vi.fn(preventDefault)}
      onSaveGlobalChatRetrieval={vi.fn(preventDefault)}
      onSaveGlobalSlot={vi.fn(preventDefault)}
      onSaveWorkspaceChatRetrieval={vi.fn(preventDefault)}
      onSaveWorkspaceOverride={vi.fn(preventDefault)}
      workspaceChatRerankCandidateLimit={10}
      workspaceChatRerankEnabled
      workspaceChatRetrievalLimit={5}
      workspaceId="11111111-1111-4111-8111-111111111111"
      workspaceRuntimeSettings={workspaceRuntimeSettings}
      workspaceSlot="chat"
      workspaceSlotConnectionId="qwen-hosted"
      workspaceSlotModelId="qwen-plus"
      providerModels={providerModels}
      slots={runtimeSlots}
      state="idle"
    />
  )
}

describe('ProviderModelCatalogView pricing', () => {
  test('shows compact USD pricing and No pricing empty state', () => {
    render(<ProviderModelCatalogView providerModels={pricedProviderModels} />)

    expect(screen.getByText('qwen-plus')).toBeTruthy()
    expect(
      screen.getByText('In $0.40 · Out $1.20 · Think $4.00 /1M'),
    ).toBeTruthy()
    expect(screen.getByText('In $0.07 /1M')).toBeTruthy()
    expect(screen.getAllByText('Priced')).toHaveLength(2)
    // Summary line + badge both say "No pricing" for unpriced models.
    const missingLines = document.querySelectorAll(
      '[data-pricing-state="missing"]',
    )
    expect(missingLines).toHaveLength(1)
    expect(missingLines[0]?.textContent).toBe('No pricing')
    expect(screen.getAllByText('No pricing').length).toBeGreaterThanOrEqual(2)
  })
})

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
      screen.getByRole('heading', { name: 'Global Defaults' }),
    ).toBeTruthy()
    expect(
      screen.queryByRole('button', { name: 'Reload Global Defaults' }),
    ).toBeNull()
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

  test('keeps legacy global button CSS removed from App styles', () => {
    expect(appStyles).not.toContain('button:not([data-slot]) {')
    expect(appStyles).not.toContain('button:not([data-slot]):disabled {')
    expect(appStyles).not.toContain(
      ":is([data-theme='dark'], [data-theme='purple']) button:not([data-slot]) {",
    )
    expect(appStyles).not.toContain(
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
    const longWorkspaceId =
      '11111111-1111-4111-8111-111111111111-workspace-with-long-runtime-id'
    renderRuntimeSettingsPanel({
      activeSubmodule: 'workspace_overrides',
      workspaceId: longWorkspaceId,
    })

    const statusBadge = screen.getByText(longWorkspaceId)
    const header = statusBadge.closest('[data-slot="panel-header"]')
    const titleGroup = screen.getByRole('heading', {
      level: 2,
      name: 'Workspace Overrides',
    }).parentElement

    expect(header?.className).toContain('flex-col')
    expect(header?.className).toContain('sm:flex-row')
    expect(titleGroup?.className).toContain('min-w-0')
    expect(statusBadge.className).toContain('max-w-full')
    expect(statusBadge.className).toContain('break-all')
  })

  test('hides the connection form until New Connection is requested', () => {
    const onRequestCreateConnection = vi.fn()
    renderRuntimeSettingsPanel({ onRequestCreateConnection })

    expect(screen.getByRole('button', { name: 'New Connection' })).toBeTruthy()
    expect(screen.queryByLabelText('Provider')).toBeNull()
    expect(screen.queryByLabelText('API Key')).toBeNull()
    expect(screen.getByText('Qwen / Hosted')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'New Connection' }))
    expect(onRequestCreateConnection).toHaveBeenCalledTimes(1)
  })

  test('keeps connection form fields label-addressable without rendering secret connection controls', () => {
    renderRuntimeSettingsPanel({ isCreatingConnection: true })

    expect(screen.getByLabelText('Provider')).toBeTruthy()
    expect(screen.getByLabelText('Connection Type')).toBeTruthy()
    expect(screen.getByLabelText('Base URL')).toBeTruthy()
    expect(screen.getByRole('combobox', { name: 'Capabilities' })).toBeTruthy()
    expect(screen.getByLabelText('API Key')).toBeTruthy()
    expect(screen.queryByLabelText('Secret Connection')).toBeNull()
    expect(screen.getByText('Qwen / Hosted')).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'New Connection' })).toBeNull()
  })

  test('places the connection form above the provider connections list', () => {
    renderRuntimeSettingsPanel({ isCreatingConnection: true })

    const form = screen.getByRole('form', { name: 'New Connection' })
    const list = screen.getByRole('region', { name: 'Provider Connections' })
    expect(
      Boolean(
        form.compareDocumentPosition(list) & Node.DOCUMENT_POSITION_FOLLOWING,
      ),
    ).toBe(true)
  })

  test('wires API key FieldHelp outside control when editing a connection', () => {
    renderRuntimeSettingsPanel({
      editingConnectionId: 'qwen-hosted',
    })

    const apiKey = screen.getByLabelText('API Key')
    expect(apiKey.getAttribute('aria-describedby')).toBe(
      'runtime-connection-api-key-help',
    )
    const help = screen.getByText(/Leave Blank to Keep the Existing Key/)
    expect(help.getAttribute('data-slot')).toBe('field-help')
    expect(help.closest('[data-slot="field-control"]')).toBeNull()
  })

  test('renders runtime form selects with the Radix Select primitive', async () => {
    const user = userEvent.setup()
    const onConnectionProviderChange = vi.fn()
    renderRuntimeSettingsPanel({
      isCreatingConnection: true,
      onConnectionProviderChange,
    })

    const providerSelect = screen.getByRole('combobox', { name: 'Provider' })
    expect(providerSelect.getAttribute('data-slot')).toBe('select-trigger')
    expect(providerSelect.getAttribute('data-state')).toBe('closed')

    await user.click(providerSelect)

    const fakeOption = await screen.findByRole('option', { name: 'Fake' })
    const field = providerSelect.closest('[data-slot="field"]')

    expect(providerSelect.getAttribute('data-state')).toBe('open')
    expect(fakeOption.closest('[data-slot="select-content"]')).toBeTruthy()
    expect(field?.contains(fakeOption)).toBe(false)

    await user.click(fakeOption)

    expect(onConnectionProviderChange).toHaveBeenCalledWith('fake')
  })

  test('uses reusable Radix selects for runtime select controls', () => {
    expect(runtimeSource).toContain("@/components/ui/select")
    expect(runtimeSource).not.toContain('NativeSelect')
    expect(runtimeSource).not.toContain('<select')
  })

  test('renders capability options through a Radix popover portal', async () => {
    const user = userEvent.setup()
    renderRuntimeSettingsPanel({ isCreatingConnection: true })

    const trigger = screen.getByRole('combobox', { name: 'Capabilities' })
    const selector = trigger.closest('[data-slot="capability-selector"]')
    expect(selector?.querySelector('.max-\\[680px\\]\\:min-h-11, [class*="min-h-11"]')).toBeTruthy()
    expect(
      Array.from(selector?.querySelectorAll('div') ?? []).some((el) =>
        el.className.includes('max-[680px]:min-h-11'),
      ),
    ).toBe(true)

    expect(trigger.getAttribute('aria-expanded')).toBe('false')
    await user.click(trigger)

    const listbox = await screen.findByRole('listbox', {
      name: 'Capability Options',
    })

    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    expect(listbox.getAttribute('data-state')).toBe('open')
    expect(listbox.className).toContain('shadow-[var(--shadow-popover)]')
    expect(screen.getByRole('option', { name: 'Add Dense Embedding Capability' })).toBeTruthy()
    expect(selector).toBeTruthy()
    expect(selector?.contains(listbox)).toBe(false)
  })

  test('delegates capability popover dismissal to Radix primitives', () => {
    expect(runtimeSource).toContain('@/components/ui/popover')
    expect(runtimeSource).not.toContain('@radix-ui/react-popover')
    expect(runtimeSource).not.toContain('document.addEventListener')
    expect(runtimeSource).not.toContain('document.removeEventListener')
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
      'Connection Check Passed: 2 Provider Models Reachable.',
    )

    expect(feedback.getAttribute('role')).toBe('status')
    expect(feedback.getAttribute('aria-live')).toBe('polite')
  })

  test('keeps failed connection checks as alerts without echoing secrets', () => {
    const connectionCheckResults: Record<string, ProviderConnectionCheckResponse> =
      {
        'qwen-hosted': {
          connection_id: 'qwen-hosted',
          message: 'provider credentials rejected sk-leakedsecret123456',
          model_count: 0,
          ok: false,
        },
      }

    renderRuntimeSettingsPanel({ connectionCheckResults })

    const alert = screen.getByRole('alert')
    expect(alert.textContent).toMatch(/Connection check failed/i)
    expect(alert.textContent).not.toContain('sk-leakedsecret123456')
    expect(alert.textContent).toContain('[redacted]')
  })

  test('enables delete confirmation only for the exact connection id', async () => {
    const user = userEvent.setup()
    render(<StatefulDeleteRuntimePanel />)

    const providerConnectionsRegion = screen.getByRole('region', {
      name: 'Provider Connections',
    })
    await user.click(
      within(providerConnectionsRegion).getByRole('button', {
        name: 'Delete qwen-hosted Connection',
      }),
    )

    const deleteForm = screen.getByRole('form', {
      name: 'Delete qwen-hosted Connection',
    })
    expect(
      within(deleteForm).getByText((_, element) => {
        return (
          element?.tagName.toLowerCase() === 'p' &&
          element.textContent === 'Type qwen-hosted to Confirm Deletion.'
        )
      }),
    ).toBeTruthy()
    const confirmation = screen.getByLabelText(
      'Confirm Connection ID',
    ) as HTMLInputElement
    const deleteButton = screen.getByRole('button', {
      name: 'Delete Connection',
    }) as HTMLButtonElement

    expect(deleteButton.disabled).toBe(true)
    await user.type(confirmation, 'wrong-id')
    expect(deleteButton.disabled).toBe(true)
    await user.clear(confirmation)
    await user.type(confirmation, 'qwen-hosted')
    expect(deleteButton.disabled).toBe(false)
  })

  test('shows loading connections instead of empty while busy', () => {
    const { container } = renderRuntimeSettingsPanel({
      connections: [],
      state: 'loading',
    })

    expect(screen.getByText('Loading Connections…')).toBeTruthy()
    expect(screen.queryByText('No runtime connections loaded.')).toBeNull()
    expect(
      container.querySelector('[data-slot-state="loading"]')?.className,
    ).toMatch(/motion-safe:animate-pulse/)
  })

  test('puts combobox ARIA on the capabilities filter input', async () => {
    const user = userEvent.setup()
    renderRuntimeSettingsPanel({ isCreatingConnection: true })

    const filter = screen.getByRole('combobox', { name: 'Capabilities' })
    expect(filter.getAttribute('aria-expanded')).toBe('false')
    expect(filter.getAttribute('aria-controls')).toBe(
      'runtime-capability-options',
    )
    await user.click(filter)
    expect(filter.getAttribute('aria-expanded')).toBe('true')
    expect(
      await screen.findByRole('listbox', { name: 'Capability Options' }),
    ).toBeTruthy()
  })

  test('shows loading catalog instead of empty while busy', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'model_catalog',
      providerModels: [],
      state: 'loading',
    })

    expect(screen.getByText('Loading Provider Models…')).toBeTruthy()
    expect(screen.queryByText('No provider models loaded.')).toBeNull()
  })

  test('uses EmptyState for empty global slots', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      slots: [],
    })

    expect(
      screen.getByText(/No Global Slot Defaults Yet\. Save a Global Slot/),
    ).toBeTruthy()
  })

  test('shows EmptyState when workspace chat pool is empty', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'workspace_overrides',
      workspaceRuntimeSettings: {
        ...workspaceRuntimeSettings,
        chat_models: [],
      },
    })

    expect(
      screen.getByText(/No Chat Models in the Workspace Pool Yet/),
    ).toBeTruthy()
  })

  test('distinguishes loading vs empty for slots and chat retrieval', () => {
    const loading = renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      chatRetrievalSettings: null,
      slots: [],
      state: 'loading',
    })
    expect(screen.getByText('Loading Global Slots…')).toBeTruthy()
    expect(screen.getByText('Loading Chat Retrieval Defaults…')).toBeTruthy()
    expect(screen.queryByText(/No Global Slot Defaults Yet/)).toBeNull()
    loading.unmount()

    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      chatModels: [],
      state: 'loading',
    })
    expect(screen.getByText('Loading Chat Models…')).toBeTruthy()
    expect(screen.queryByText('No Chat Models Yet.')).toBeNull()
  })

  test('shows canceled instead of empty for connections and chat models', () => {
    const connections = renderRuntimeSettingsPanel({
      connections: [],
      state: 'canceled',
    })
    expect(screen.getByText('Connections Load Canceled.')).toBeTruthy()
    expect(
      screen.getByText('Connections Load Canceled.').closest('[data-slot-state="canceled"]'),
    ).toBeTruthy()
    expect(screen.queryByText('No Connections Yet.')).toBeNull()
    connections.unmount()

    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      chatModels: [],
      chatRetrievalSettings: null,
      slots: [],
      state: 'canceled',
    })
    expect(screen.getByText('Chat Models Load Canceled.')).toBeTruthy()
    expect(screen.getByText('Global Slots Load Canceled.')).toBeTruthy()
    expect(screen.getByText('Chat Retrieval Defaults Load Canceled.')).toBeTruthy()
    expect(screen.queryByText('No Chat Models Yet.')).toBeNull()
  })

  test('select placeholders say loading instead of empty while busy', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      chatConnectionId: '',
      chatModelId: '',
      connections: [],
      globalSlotConnectionId: '',
      globalSlotModelId: '',
      providerModels: [],
      state: 'loading',
    })

    expect(screen.getAllByText('Loading Connections…').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Loading Models…').length).toBeGreaterThan(0)
    expect(screen.queryByText('No Connections Yet')).toBeNull()
    expect(screen.queryByText('No Models Yet')).toBeNull()
  })

  test('shows EmptyState when workspace effective slots are empty', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'workspace_overrides',
      workspaceRuntimeSettings: {
        ...workspaceRuntimeSettings,
        slots: [],
      },
    })

    expect(screen.getByText('No Effective Slots Yet.')).toBeTruthy()
    expect(
      screen.getByText('No Effective Slots Yet.').closest('[data-slot-state="empty"]'),
    ).toBeTruthy()
  })
})
