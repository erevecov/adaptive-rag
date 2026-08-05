/**
 * @vitest-environment jsdom
 */
import { type FormEvent, useState } from 'react'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import appSource from '@/App.tsx?raw'
import runtimeSource from './RuntimeSettingsView.tsx?raw'
import { RuntimeSettingsPanel } from './RuntimeSettingsView'
import { installPointerEventMocks } from '@/test/pointerEvents'
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
      screen.getByRole('heading', { name: 'Global Defaults' }),
    ).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Reload Global Defaults' })).toBeTruthy()
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
      name: 'Project Overrides',
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
    expect(screen.getByLabelText('Connection Type')).toBeTruthy()
    expect(screen.getByLabelText('Base URL')).toBeTruthy()
    expect(screen.getByRole('combobox', { name: 'Capabilities' })).toBeTruthy()
    expect(screen.getByLabelText('API key')).toBeTruthy()
    expect(screen.queryByLabelText('Secret connection')).toBeNull()
    expect(screen.getByText('Qwen / Hosted')).toBeTruthy()
  })

  test('wires API key FieldHelp outside control when editing a connection', () => {
    renderRuntimeSettingsPanel({
      editingConnectionId: 'qwen-hosted',
    })

    const apiKey = screen.getByLabelText('API key')
    expect(apiKey.getAttribute('aria-describedby')).toBe(
      'runtime-connection-api-key-help',
    )
    const help = screen.getByText(/Leave blank to keep the existing key/)
    expect(help.getAttribute('data-slot')).toBe('field-help')
    expect(help.closest('[data-slot="field-control"]')).toBeNull()
  })

  test('renders runtime form selects with the Radix Select primitive', async () => {
    const user = userEvent.setup()
    const onConnectionProviderChange = vi.fn()
    renderRuntimeSettingsPanel({ onConnectionProviderChange })

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
    renderRuntimeSettingsPanel()

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
      name: 'Capability options',
    })

    expect(trigger.getAttribute('aria-expanded')).toBe('true')
    expect(listbox.getAttribute('data-state')).toBe('open')
    expect(listbox.className).toContain('shadow-[var(--shadow-popover)]')
    expect(screen.getByRole('option', { name: 'Add Dense Embedding capability' })).toBeTruthy()
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
      'Connection check passed: 2 provider models reachable.',
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
    renderRuntimeSettingsPanel()

    const filter = screen.getByRole('combobox', { name: 'Capabilities' })
    expect(filter.getAttribute('aria-expanded')).toBe('false')
    expect(filter.getAttribute('aria-controls')).toBe(
      'runtime-capability-options',
    )
    await user.click(filter)
    expect(filter.getAttribute('aria-expanded')).toBe('true')
    expect(
      await screen.findByRole('listbox', { name: 'Capability options' }),
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
      screen.getByText(/No global slot defaults yet\. Save a global slot/),
    ).toBeTruthy()
  })

  test('shows EmptyState when project chat pool is empty', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'project_overrides',
      projectRuntimeSettings: {
        ...projectRuntimeSettings,
        chat_models: [],
      },
    })

    expect(
      screen.getByText(/No chat models in the project pool yet/),
    ).toBeTruthy()
  })

  test('distinguishes loading vs empty for slots and chat retrieval', () => {
    const loading = renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      chatRetrievalSettings: null,
      slots: [],
      state: 'loading',
    })
    expect(screen.getByText('Loading global slots…')).toBeTruthy()
    expect(screen.getByText('Loading chat retrieval defaults…')).toBeTruthy()
    expect(screen.queryByText(/No global slot defaults yet/)).toBeNull()
    loading.unmount()

    renderRuntimeSettingsPanel({
      activeSubmodule: 'global_defaults',
      chatModels: [],
      state: 'loading',
    })
    expect(screen.getByText('Loading Chat Models…')).toBeTruthy()
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

  test('shows EmptyState when project effective slots are empty', () => {
    renderRuntimeSettingsPanel({
      activeSubmodule: 'project_overrides',
      projectRuntimeSettings: {
        ...projectRuntimeSettings,
        slots: [],
      },
    })

    expect(screen.getByText('No effective slots yet.')).toBeTruthy()
    expect(
      screen.getByText('No effective slots yet.').closest('[data-slot-state="empty"]'),
    ).toBeTruthy()
  })
})
