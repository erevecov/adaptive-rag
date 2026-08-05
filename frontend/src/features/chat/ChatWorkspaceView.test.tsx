/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type {
  ChatHistoryProviderUsage,
  ChatResponseBody,
  KnowledgeProposal,
} from '@/lib/apiClient'
import { ChatWorkspacePanel } from './ChatWorkspaceView'
import chatWorkspaceSource from './ChatWorkspaceView.tsx?raw'

afterEach(() => {
  cleanup()
})

const response: ChatResponseBody = {
  answer: 'Use the indexed architecture notes.',
  citations: [
    {
      chunk_id: 'chunk-1',
      citation: {
        char_end: 48,
        char_start: 0,
        chunk_id: 'chunk-1',
        document_id: 'doc-1',
        document_stable_id: 'architecture',
        document_version_id: 'version-1',
        document_version_number: 3,
        section_metadata: null,
        snippet: 'Architecture notes mention adaptive retrieval.',
        source_external_id: 'architecture.md',
        source_extra_metadata: null,
        source_id: 'source-1',
        source_tags: [],
        source_type: 'markdown',
      },
      distance: 0.1,
      embedding_metadata: null,
      score: 0.82,
    },
  ],
  session_id: 'session-1',
  tool_calls: [
    {
      limit: 3,
      name: 'retrieve',
      query: 'architecture notes',
      result_count: 1,
    },
  ],
}

const providerUsage: ChatHistoryProviderUsage[] = [
  {
    created_at: '2026-06-21T00:00:00Z',
    currency: 'USD',
    error_message: null,
    estimated_cost_usd: 0.0123,
    input_count: null,
    input_tokens: 120,
    latency_ms: 430,
    model: 'qwen-plus',
    operation: 'chat',
    output_tokens: 32,
    provider: 'qwen',
    provider_request_id: 'request-1',
    provider_usage_id: 'usage-1',
    status: 'succeeded',
    total_tokens: 152,
    usage_source: 'provider_reported',
  },
]

function renderChatWorkspace(
  overrides: Partial<React.ComponentProps<typeof ChatWorkspacePanel>> = {},
) {
  const props: React.ComponentProps<typeof ChatWorkspacePanel> = {
    activeResponseQuestion: 'What do the architecture notes say?',
    drafts: {},
    isAsking: false,
    isContextInspectorActive: false,
    isMinimapInspectorActive: false,
    isSpeechSupported: true,
    onCancelRequest: vi.fn(),
    onOpenContextInspector: vi.fn(),
    onOpenMinimapInspector: vi.fn(),
    onOpenSource: vi.fn(),
    onQuestionChange: vi.fn(),
    onRefineKnowledgeDraft: vi.fn(),
    onStartSpeechRecognition: vi.fn(),
    onStopSpeechRecognition: vi.fn(),
    onSubmit: vi.fn((event) => event.preventDefault()),
    onSubmitKnowledgeDraft: vi.fn(async () => knowledgeProposal),
    providerUsage,
    question: '',
    requestError: null,
    requestState: 'succeeded',
    response,
    setDrafts: vi.fn(),
    speechFeedback: null,
    speechState: 'idle',
    ...overrides,
  }

  return {
    props,
    view: render(<ChatWorkspacePanel {...props} />),
  }
}

const knowledgeProposal: KnowledgeProposal = {
  approved_source_id: null,
  created_at: '2026-06-21T00:00:00Z',
  id: 'proposal-1',
  origin_message_id: null,
  origin_session_id: 'session-1',
  project_id: 'project-1',
  proposed_text: 'Persist this fact',
  refined_text: 'Refined draft text',
  review_note: null,
  reviewed_at: null,
  reviewed_by_user_id: null,
  status: 'pending',
  submitted_by_user_id: 'user-1',
  updated_at: '2026-06-21T00:00:00Z',
}

function expectNoLegacyChatClasses(container: HTMLElement) {
  expect(container.querySelector('.chat-form')).toBeNull()
  expect(container.querySelector('.speech-input')).toBeNull()
  expect(container.querySelector('.message-card')).toBeNull()
  expect(container.querySelector('.response-details-panel')).toBeNull()
  expect(container.querySelector('.chat-question-pill')).toBeNull()
  expect(container.querySelector('.source-viewer-button')).toBeNull()
}

describe('ChatWorkspacePanel', () => {
  test('cancel request button uses a destructive secondary tone while asking', () => {
    renderChatWorkspace({ isAsking: true, question: 'Stop me' })

    const cancel = screen.getByRole('button', { name: 'Cancel' })
    expect(cancel.className).toMatch(/border-destructive\/30/)
    expect(cancel.className).toMatch(/text-destructive/)
    expect(cancel.getAttribute('data-slot')).toBe('button')
  })

  test('renders the composer with tokenized controls and actions', async () => {
    const user = userEvent.setup()
    const onQuestionChange = vi.fn()
    const base = renderChatWorkspace({
      onQuestionChange,
      response: null,
    })
    base.view.unmount()

    function QuestionHarness() {
      const [question, setQuestion] = useState('')
      return (
        <ChatWorkspacePanel
          {...base.props}
          onQuestionChange={(value) => {
            setQuestion(value)
            onQuestionChange(value)
          }}
          question={question}
          response={null}
        />
      )
    }

    const view = render(<QuestionHarness />)

    const workspace = screen.getByRole('region', { name: 'Chat workspace' })
    expect(workspace.getAttribute('data-slot')).toBe('panel')
    expect(screen.getByLabelText('Question').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(screen.getByRole('button', { name: 'Start transcript' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Ask' }).getAttribute('data-slot')).toBe(
      'button',
    )

    await user.type(screen.getByLabelText('Question'), 'hello')
    expect(onQuestionChange).toHaveBeenLastCalledWith('hello')

    expectNoLegacyChatClasses(view.container)
  })

  test('shows response details with data-list rows and source actions', async () => {
    const user = userEvent.setup()
    const { props, view } = renderChatWorkspace()

    await user.click(
      screen.getByRole('button', { name: 'Expand response details' }),
    )

    expect(screen.getByRole('region', { name: 'Tool calls detail' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Sources detail' })).toBeTruthy()
    expect(view.container.querySelector('[data-slot="data-list"]')).toBeTruthy()
    expect(screen.getByText('$0.0123')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'View source architecture.md' }))
    expect(props.onOpenSource).toHaveBeenCalledWith(
      'source-1',
      'Architecture notes mention adaptive retrieval.',
    )
    expectNoLegacyChatClasses(view.container)
  })

  test('renders citation chips under the answer card', async () => {
    const user = userEvent.setup()
    const onOpenSource = vi.fn()
    const { view } = renderChatWorkspace({
      onOpenSource,
      requestState: 'succeeded',
      response,
    })
    const chip = screen.getByRole('button', { name: 'architecture.md' })
    expect(
      view.container.querySelector('[data-slot="chat-answer-citations"]'),
    ).toBeTruthy()
    await user.click(chip)
    expect(onOpenSource).toHaveBeenCalledWith(
      'source-1',
      'Architecture notes mention adaptive retrieval.',
    )
  })

  test('renders waiting and error states with feedback primitives', () => {
    const { view } = renderChatWorkspace({
      requestError: 'Request failed',
      requestState: 'loading',
      response: null,
    })

    const loading = view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="loading"]',
    )
    expect(loading).toBeTruthy()
    expect(loading?.textContent).toContain('Waiting for response...')
    expect(screen.getByRole('alert').textContent).toContain('Request failed')
    expect(view.container.querySelector('[data-slot="chat-composer"]')).toBeTruthy()
    expect(
      view.container.querySelector('[data-slot="chat-composer-actions"]'),
    ).toBeTruthy()
    expect(
      view.container
        .querySelector('[data-slot="chat-transcript"]')
        ?.getAttribute('aria-busy'),
    ).toBe('true')
    expectNoLegacyChatClasses(view.container)
    view.unmount()

    const failed = renderChatWorkspace({
      requestError: 'Upstream timeout',
      requestState: 'failed',
      response: null,
    })
    const failedState = failed.view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="failed"]',
    )
    expect(failedState).toBeTruthy()
    expect(failedState?.textContent).toContain('Request failed.')
    expect(failedState?.getAttribute('role')).toBe('alert')
    failed.view.unmount()

    const canceled = renderChatWorkspace({
      requestState: 'canceled',
      response: null,
    })
    const canceledState = canceled.view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="canceled"]',
    )
    expect(canceledState).toBeTruthy()
    expect(canceledState?.textContent).toContain('Request canceled.')
    canceled.view.unmount()
  })

  test('renders empty transcript and beflow-like composer layout', () => {
    const empty = renderChatWorkspace({
      requestState: 'idle',
      response: null,
    })
    const emptyState = empty.view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="empty"]',
    )
    expect(emptyState).toBeTruthy()
    expect(emptyState?.textContent).toContain('No response yet.')
    expect(emptyState?.textContent).toMatch(/Enter to send/)
    expect(screen.queryByText('Speech input ready.')).toBeNull()
    const composer = empty.view.container.querySelector('[data-slot="chat-composer"]')
    expect(composer?.className).toMatch(/max-w-3xl/)
    expect(screen.getByLabelText('Question').className).toMatch(/rounded-xl/)
    expect(screen.getByRole('button', { name: 'Ask' }).textContent).toMatch(/Ask/)
    empty.view.unmount()

    const { view } = renderChatWorkspace()
    const workspace = screen.getByRole('region', { name: 'Chat workspace' })
    expect(
      view.container.querySelector('[data-slot="chat-transcript"]')?.parentElement,
    ).toBe(workspace)
    expect(
      view.container.querySelector('[data-slot="chat-composer-shell"]')?.parentElement,
    ).toBe(workspace)
    expect(view.container.querySelector('[data-slot="chat-message"]')).toBeTruthy()
  })

  test('renders knowledge draft actions with editable text', () => {
    const draftResponse: ChatResponseBody = {
      ...response,
      tool_calls: [
        {
          arguments: { knowledge_text: 'Persist this fact' },
          name: 'commit_knowledge',
          result_summary: {
            draft_id: 'draft-1',
            proposed_text: 'Persist this fact',
            review_action: 'approve',
            scope: 'project',
            status: 'draft',
          },
        },
      ],
    }
    const { view } = renderChatWorkspace({
      drafts: {
        'draft-1': {
          draftId: 'draft-1',
          error: null,
          proposalId: null,
          reviewAction: 'approve',
          scope: 'project',
          status: 'draft',
          text: 'Persist this fact',
        },
      },
      response: draftResponse,
    })

    const draft = screen.getByRole('region', { name: 'Knowledge draft draft-1' })
    expect(within(draft).getByLabelText('Knowledge draft text')).toBeTruthy()
    expect(within(draft).getByRole('button', { name: 'Approve knowledge' })).toBeTruthy()
    expect(within(draft).getByText('draft').getAttribute('data-tone')).toBe('primary')
    expectNoLegacyChatClasses(view.container)
  })

  test('maps knowledge draft status badges to lifecycle tones', () => {
    const statuses = [
      { status: 'draft', tone: 'primary' },
      { status: 'pending', tone: 'warning' },
      { status: 'approved', tone: 'success' },
      { status: 'cancelled', tone: 'neutral' },
    ] as const

    for (const { status, tone } of statuses) {
      cleanup()
      renderChatWorkspace({
        drafts: {
          [status]: {
            draftId: status,
            error: null,
            proposalId: status === 'pending' ? 'proposal-1' : null,
            reviewAction: 'approve',
            scope: 'project',
            status,
            text: `Text for ${status}`,
          },
        },
        response,
      })

      const card = screen.getByRole('region', { name: `Knowledge draft ${status}` })
      expect(within(card).getByText(status).getAttribute('data-tone')).toBe(tone)
    }
  })

  test('uses lucide icons instead of inline SVG icon functions', () => {
    expect(chatWorkspaceSource).toContain('lucide-react')
    expect(chatWorkspaceSource).not.toContain('<svg')
    expect(chatWorkspaceSource).not.toContain('function ContextRingIcon')
    expect(chatWorkspaceSource).not.toContain('function MinimapIcon')
    expect(chatWorkspaceSource).not.toContain('function TranscriptIcon')
    expect(chatWorkspaceSource).not.toContain('function SendIcon')
    expect(chatWorkspaceSource).not.toContain('ui-icon')
  })
})
