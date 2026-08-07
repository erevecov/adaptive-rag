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

    const cancel = screen.getByRole('button', { name: 'Cancel Request' })
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

    const workspace = screen.getByRole('region', { name: 'Chat Workspace' })
    expect(workspace.getAttribute('data-slot')).toBe('panel')
    expect(screen.getByLabelText('Question').getAttribute('data-slot')).toBe(
      'textarea',
    )
    expect(screen.getByRole('button', { name: 'Start Transcript' })).toBeTruthy()
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
      screen.getByRole('button', { name: 'Expand Response Details' }),
    )

    expect(screen.getByRole('region', { name: 'Tool Calls Detail' })).toBeTruthy()
    expect(screen.getByRole('region', { name: 'Sources Detail' })).toBeTruthy()
    expect(view.container.querySelector('[data-slot="data-list"]')).toBeTruthy()
    expect(screen.getByText('$0.0123')).toBeTruthy()

    await user.click(
      within(screen.getByRole('region', { name: 'Sources Detail' })).getByRole(
        'button',
        { name: 'View Source architecture.md' },
      ),
    )
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
    const chip = screen.getByRole('button', { name: 'Open Source architecture.md' })
    expect(
      view.container.querySelector('[data-slot="chat-answer-citations"]'),
    ).toBeTruthy()
    expect(chip.textContent).toMatch(/1/)
    expect(chip.textContent).toContain('architecture.md')
    expect(chip.getAttribute('title')).toContain(
      'Architecture notes mention adaptive retrieval.',
    )
    expect(chip.className).toMatch(/hover:bg-primary\/15/)
    expect(chip.className).toMatch(/max-\[680px\]:min-h-11/)
    expect(
      view.container.querySelector('[data-slot="chat-message"]')?.className,
    ).toMatch(/focus-within:border-primary/)
    expect(
      view.container.querySelector('[data-slot="chat-message"]')?.className,
    ).not.toMatch(/focus-within:border-primary\/40/)
    expect(
      view.container.querySelector('[data-slot="chat-message"]')?.className,
    ).toMatch(/(?:^|\s)border-border(?:\s|$)/)
    expect(
      view.container.querySelector('[data-slot="chat-message"]')?.className,
    ).not.toMatch(/border-border\/70/)
    expect(
      view.container.querySelector('[data-slot="chat-answer-citations"]')?.className,
    ).toMatch(/(?:^|\s)border-border(?:\s|$)/)
    expect(screen.getByText('Answer')).toBeTruthy()
    await user.click(chip)
    expect(onOpenSource).toHaveBeenCalledWith(
      'source-1',
      'Architecture notes mention adaptive retrieval.',
    )
  })

  test('shows thread continuity and composer keyboard shortcuts', () => {
    const { view } = renderChatWorkspace({
      continuingSessionId: 'session-abcdef12-3456',
      response: null,
      requestState: 'idle',
    })

    const continuity = view.container.querySelector(
      '[data-slot="chat-session-continuity"]',
    )
    expect(continuity).toBeTruthy()
    expect(continuity?.textContent).toContain('Continuing thread')
    expect(continuity?.textContent).toContain('session-')

    const shortcuts = view.container.querySelector(
      '[data-slot="chat-composer-shortcuts"]',
    )
    expect(shortcuts).toBeTruthy()
    expect(shortcuts?.textContent).toMatch(/Enter/)
    expect(shortcuts?.textContent).toMatch(/Send/)
    expect(shortcuts?.textContent).toMatch(/New line/)
    expect(shortcuts?.textContent).not.toMatch(/Cancel/)
    view.unmount()

    const asking = renderChatWorkspace({
      continuingSessionId: 'session-1',
      isAsking: true,
      question: 'still going',
      requestState: 'loading',
      response: null,
    })
    expect(
      asking.view.container.querySelector(
        '[data-slot="chat-composer-shortcuts"]',
      )?.textContent,
    ).toMatch(/Cancel/)
  })

  test('renders waiting and error states with feedback primitives', () => {
    const { view } = renderChatWorkspace({
      requestState: 'loading',
      response: null,
    })

    const loading = view.container.querySelector(
      '[data-slot="empty-state"][data-slot-state="loading"]',
    )
    expect(loading).toBeTruthy()
    expect(loading?.textContent).toContain('Waiting for response…')
    // Errors are co-located with the transcript failure state, not under the
    // composer while the request is still loading.
    expect(screen.queryByRole('alert')).toBeNull()
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
    expect(failedState?.textContent).toContain('Request failed')
    expect(failedState?.textContent).toContain('Upstream timeout')
    expect(
      failed.view.container.querySelector('[data-slot="chat-error-detail"]')
        ?.textContent,
    ).toContain('Upstream timeout')
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
    expect(canceledState?.textContent).toContain('Request canceled')
    canceled.view.unmount()

    const canceledPartial = renderChatWorkspace({
      requestState: 'canceled',
      response,
    })
    const canceledBanner = canceledPartial.view.container.querySelector(
      '[data-slot="chat-terminal-banner"][data-slot-state="canceled"]',
    )
    expect(canceledBanner).toBeTruthy()
    expect(canceledBanner?.textContent).toMatch(/Stopped — partial answer/)
    expect(canceledBanner?.querySelector('[role="status"]')).toBeTruthy()
    expect(
      canceledPartial.view.container.querySelector('[data-slot="chat-message"]'),
    ).toBeTruthy()
    canceledPartial.view.unmount()

    const failedPartial = renderChatWorkspace({
      requestError: 'Upstream timeout',
      requestState: 'failed',
      response,
    })
    const failedBanner = failedPartial.view.container.querySelector(
      '[data-slot="chat-terminal-banner"][data-slot-state="failed"]',
    )
    expect(failedBanner).toBeTruthy()
    expect(failedBanner?.textContent).toContain('Upstream timeout')
    expect(failedBanner?.querySelector('[role="alert"]')).toBeTruthy()
    failedPartial.view.unmount()
  })

  test('shows regenerate for succeeded answers and wires the handler', async () => {
    const userDriver = userEvent.setup()
    const onRegenerateLastAnswer = vi.fn()
    const { view } = renderChatWorkspace({
      onRegenerateLastAnswer,
      requestState: 'succeeded',
      response,
    })

    const regenerate = screen.getByRole('button', { name: 'Regenerate answer' })
    expect(regenerate.textContent).toMatch(/Regenerate/)
    await userDriver.click(regenerate)
    expect(onRegenerateLastAnswer).toHaveBeenCalledTimes(1)
    view.unmount()
  })

  test('edit question loads text into the composer via onEditQuestion', async () => {
    const userDriver = userEvent.setup()
    const onEditQuestion = vi.fn()
    renderChatWorkspace({
      activeResponseQuestion: 'What is Nimbus?',
      onEditQuestion,
      requestState: 'succeeded',
      response,
    })

    await userDriver.click(screen.getByRole('button', { name: 'Edit question' }))
    expect(onEditQuestion).toHaveBeenCalledWith('What is Nimbus?')
  })

  test('context window chip shows summarized counts from context step', () => {
    const responseWithContext = {
      ...response,
      steps: [
        {
          id: 'context',
          status: 'done' as const,
          detail: {
            total_messages: 20,
            kept_recent: 8,
            summarized_messages: 12,
            used_summary: true,
            summary_preview: 'Pinned user-stated facts…',
          },
        },
      ],
    }
    const { view } = renderChatWorkspace({
      continuingSessionId: 'session-1',
      priorTurns: [
        {
          id: 't1',
          question: 'Earlier Q',
          answer: 'Earlier A',
          citations: [],
          steps: [],
          tool_calls: [],
        },
      ],
      response: responseWithContext,
      requestState: 'succeeded',
    })
    const chip = view.container.querySelector('[data-slot="chat-context-window"]')
    expect(chip).toBeTruthy()
    expect(chip?.textContent).toMatch(/8 recent/)
    expect(chip?.textContent).toMatch(/12 summarized/)
  })

  test('retry button appears on failed empty state with error detail', async () => {
    const userDriver = userEvent.setup()
    const onRetryLastQuestion = vi.fn()
    renderChatWorkspace({
      activeResponseQuestion: 'What is Nimbus?',
      onRetryLastQuestion,
      requestError:
        'Chat provider rate-limited the request (HTTP 429). Wait a moment and use Try again.',
      requestState: 'failed',
      response: null,
    })

    expect(
      screen.getByText(/Chat provider rate-limited the request \(HTTP 429\)/),
    ).toBeTruthy()
    await userDriver.click(screen.getByRole('button', { name: 'Try again' }))
    expect(onRetryLastQuestion).toHaveBeenCalledTimes(1)
  })

  test('Enter on empty question does not submit', async () => {
    const userDriver = userEvent.setup()
    const onSubmit = vi.fn((event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault()
    })
    const { view } = renderChatWorkspace({
      onSubmit,
      question: '   ',
      requestState: 'idle',
      response: null,
    })

    await userDriver.type(screen.getByLabelText('Question'), '{Enter}')
    expect(onSubmit).not.toHaveBeenCalled()
    expect(
      view.container.querySelector(
        '[data-slot="empty-state"][data-slot-state="failed"]',
      ),
    ).toBeNull()
    expect(
      view.container.querySelector(
        '[data-slot="empty-state"][data-slot-state="empty"]',
      ),
    ).toBeTruthy()
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
    expect(emptyState?.textContent).toContain('No response yet')
    expect(emptyState?.textContent).toMatch(/Enter to send/)
    expect(
      empty.view.container.querySelector('[data-slot="chat-sample-questions"]'),
    ).toBeTruthy()
    expect(screen.queryByText('Speech input ready.')).toBeNull()
    const composer = empty.view.container.querySelector('[data-slot="chat-composer"]')
    expect(composer?.className).toMatch(/max-w-3xl/)
    expect(screen.getByLabelText('Question').className).toMatch(/rounded-xl/)
    expect(screen.getByRole('button', { name: 'Ask' }).textContent).toMatch(/Ask/)
    expect(screen.getByRole('button', { name: 'Ask' }).className).toMatch(
      /max-\[680px\]:min-h-11/,
    )
    expect(screen.getByRole('button', { name: 'Ask' }).className).toMatch(
      /max-\[680px\]:w-full/,
    )
    expect(screen.getByLabelText('Question').className).toMatch(/border-border/)
    expect(screen.getByLabelText('Question').className).not.toMatch(
      /border-border\/50/,
    )
    expect(
      screen.getByRole('button', { name: 'Open Context Sidebar' }).className,
    ).toMatch(/max-\[680px\]:min-h-11/)
    expect(
      screen.getByRole('button', { name: 'Open Context Sidebar' }).className,
    ).toMatch(/hover:bg-primary\/15/)
    expect(
      screen.getByRole('button', { name: 'Open Context Sidebar' }).className,
    ).not.toMatch(/hover:bg-muted/)
    empty.view.unmount()

    const { view } = renderChatWorkspace()
    const workspace = screen.getByRole('region', { name: 'Chat Workspace' })
    expect(
      view.container.querySelector('[data-slot="chat-transcript"]')?.parentElement,
    ).toBe(workspace)
    expect(
      view.container.querySelector('[data-slot="chat-composer-shell"]')?.parentElement,
    ).toBe(workspace)
    expect(
      view.container.querySelector('[data-slot="chat-composer-shell"]')?.className,
    ).toMatch(/max-\[680px\]:sticky/)
    expect(
      view.container.querySelector('[data-slot="chat-composer-shell"]')?.className,
    ).toMatch(/max-\[680px\]:shadow-primary\/65/)
    // Height chain: panel fills its host, transcript scrolls, composer pins bottom.
    expect(workspace.className).toMatch(/(?:^|\s)h-full(?:\s|$)/)
    expect(workspace.className).toMatch(/grid-rows-\[minmax\(0,1fr\)_auto\]/)
    const transcript = view.container.querySelector('[data-slot="chat-transcript"]')
    expect(transcript?.className).toMatch(/overflow-y-auto/)
    expect(transcript?.className).toMatch(/min-h-0/)
    expect(transcript?.className).toMatch(/scrollbar-chat/)
    expect(
      view.container.querySelector('[data-slot="chat-composer-shell"]')?.className,
    ).toMatch(/shrink-0/)
    expect(screen.getByLabelText('Question').className).toMatch(/scrollbar-chat/)
    expect(view.container.querySelector('[data-slot="chat-message"]')).toBeTruthy()
  })

  test('renders the user question on a plomo bubble surface distinct from the answer', () => {
    const { view } = renderChatWorkspace({
      activeResponseQuestion: 'What is Nimbus?',
      requestState: 'succeeded',
      response,
    })

    const sticky = view.container.querySelector('[data-slot="chat-question-sticky"]')
    expect(sticky).toBeTruthy()
    expect(sticky?.className).toMatch(/bg-chat-user-bubble/)
    expect(sticky?.className).toMatch(/(?:^|\s)sticky(?:\s|$)/)
    const surface = view.container.querySelector(
      '[data-slot="chat-question-surface"]',
    )
    expect(surface).toBeTruthy()
    expect(surface?.className).toMatch(/bg-chat-user-bubble/)
    expect(surface?.className).not.toMatch(/bg-muted\//)
    const answer = view.container.querySelector('[data-slot="chat-message"]')
    expect(answer?.className).toMatch(/bg-card/)
    expect(answer?.className).not.toMatch(/bg-chat-user-bubble/)
  })

  test('prior turn questions flow normally while the current question stays sticky', () => {
    const { view } = renderChatWorkspace({
      continuingSessionId: 'session-1',
      priorTurns: [
        {
          id: 't1',
          question: 'Earlier question one',
          answer: 'Earlier answer one',
          citations: [],
          steps: [],
          tool_calls: [],
        },
        {
          id: 't2',
          question: 'Earlier question two',
          answer: 'Earlier answer two',
          citations: [],
          steps: [],
          tool_calls: [],
        },
      ],
      requestState: 'succeeded',
      response,
    })

    const strips = view.container.querySelectorAll(
      '[data-slot="chat-question-sticky"]',
    )
    expect(strips.length).toBe(3)
    expect(strips[0]?.className).not.toMatch(/(?:^|\s)sticky(?:\s|$)/)
    expect(strips[1]?.className).not.toMatch(/(?:^|\s)sticky(?:\s|$)/)
    expect(strips[2]?.className).toMatch(/(?:^|\s)sticky(?:\s|$)/)
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
          approvedSourceId: null,
          draftId: 'draft-1',
          error: null,
          ingestStatus: null,
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
    expect(within(draft).getByLabelText('Knowledge Draft Text')).toBeTruthy()
    const approve = within(draft).getByRole('button', { name: 'Approve Knowledge' })
    expect(approve).toBeTruthy()
    expect((approve as HTMLButtonElement).disabled).toBe(false)
    expect(within(draft).getByText('Draft').getAttribute('data-tone')).toBe('primary')
    expectNoLegacyChatClasses(view.container)
  })

  test('disables knowledge draft primary action when status is not draft', () => {
    for (const status of ['pending', 'approved', 'cancelled'] as const) {
      cleanup()
      renderChatWorkspace({
        drafts: {
          [status]: {
            approvedSourceId: null,
            draftId: status,
            error: null,
            ingestStatus: null,
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
      expect(
        (
          within(card).getByRole('button', {
            name: 'Approve Knowledge',
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(true)
      expect(
        (
          within(card).getByRole('button', {
            name: 'Refine In Chat',
          }) as HTMLButtonElement
        ).disabled,
      ).toBe(true)
    }
  })

  test('exposes aria-pressed on composer context and minimap tools', () => {
    const { view } = renderChatWorkspace({
      isContextInspectorActive: true,
      isMinimapInspectorActive: false,
    })

    expect(
      screen.getByRole('button', { name: 'Open Context Sidebar' }).getAttribute(
        'aria-pressed',
      ),
    ).toBe('true')
    expect(
      screen.getByRole('button', { name: 'Open Minimap Sidebar' }).getAttribute(
        'aria-pressed',
      ),
    ).toBe('false')
    expect(view.container.querySelector('#chat-composer')).toBeTruthy()
  })

  test('stacks speech status full-width under the mic on narrow layouts', () => {
    const { view } = renderChatWorkspace({
      speechFeedback: 'Listening…',
      speechState: 'loading',
    })

    const status = view.container.querySelector('[data-slot="speech-status"]')
    expect(status).toBeTruthy()
    expect(status?.textContent).toContain('Listening…')
    expect(status?.className).toMatch(/max-\[680px\]:basis-full/)
    expect(status?.className).toMatch(/max-\[680px\]:order-last/)
    expect(
      view.container.querySelector('[data-slot="speech-input"]')?.className,
    ).toMatch(/flex-wrap/)
  })

  test('shows terminal banner when cancel/fail keeps a partial response', () => {
    const canceled = renderChatWorkspace({
      requestState: 'canceled',
      response: { ...response, answer: 'Partial before cancel' },
    })
    const banner = canceled.view.container.querySelector(
      '[data-slot="chat-terminal-banner"][data-slot-state="canceled"]',
    )
    expect(banner).toBeTruthy()
    expect(banner?.textContent).toMatch(/Stopped — partial answer/)
    expect(screen.getByText('Partial before cancel')).toBeTruthy()
    canceled.view.unmount()

    const failed = renderChatWorkspace({
      requestState: 'failed',
      response: { ...response, answer: 'Partial before fail' },
    })
    expect(
      failed.view.container.querySelector(
        '[data-slot="chat-terminal-banner"][data-slot-state="failed"]',
      )?.textContent,
    ).toMatch(/Request failed/)
    expect(screen.getByRole('alert').textContent).toMatch(/incomplete/)
    failed.view.unmount()
  })

  test('blocks Enter submit while asking and cancels on Escape', async () => {
    const user = userEvent.setup()
    const onCancelRequest = vi.fn()
    const onSubmit = vi.fn((event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault()
    })
    renderChatWorkspace({
      isAsking: true,
      onCancelRequest,
      onSubmit,
      question: 'still typing',
      requestState: 'loading',
      response: null,
    })

    const textarea = screen.getByLabelText('Question')
    await user.click(textarea)
    await user.keyboard('{Enter}')
    expect(onSubmit).not.toHaveBeenCalled()

    await user.keyboard('{Escape}')
    expect(onCancelRequest).toHaveBeenCalledTimes(1)
  })

  test('maps knowledge draft status badges to lifecycle tones', () => {
    const statuses = [
      { status: 'draft', label: 'Draft', tone: 'primary' },
      { status: 'pending', label: 'Pending', tone: 'warning' },
      { status: 'approved', label: 'Approved', tone: 'success' },
      { status: 'cancelled', label: 'Canceled', tone: 'neutral' },
    ] as const

    for (const { status, label, tone } of statuses) {
      cleanup()
      renderChatWorkspace({
        drafts: {
          [status]: {
            approvedSourceId: null,
            draftId: status,
            error: null,
            ingestStatus: null,
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
      expect(within(card).getByText(label).getAttribute('data-tone')).toBe(tone)
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
