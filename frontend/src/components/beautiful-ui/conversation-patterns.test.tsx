/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { createRef } from 'react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { ChatSurface } from './chat-surface'
import { ContextChunkList } from './context-chunk-list'
import { PromptComposer } from './prompt-composer'
import { StreamingAnswer } from './streaming-answer'

afterEach(() => {
  cleanup()
})

describe('PromptComposer', () => {
  test('accepts a feature-owned composer body and forwards form attributes without duplicating input state', () => {
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    render(
      <PromptComposer
        className="feature-composer"
        content={<textarea aria-label="Feature question" defaultValue="Owned by feature" />}
        formProps={{ id: 'feature-composer', tabIndex: -1 }}
        onPromptChange={() => undefined}
        onSubmit={onSubmit}
        prompt="catalog prompt must not render"
        promptLabel="Feature composer"
        submitLabel="Send"
      />,
    )

    const form = screen.getByRole('form', { name: 'Feature composer' })
    expect(form.className).toContain('feature-composer')
    expect(form.id).toBe('feature-composer')
    expect(form.tabIndex).toBe(-1)
    expect(screen.getAllByRole('textbox')).toHaveLength(1)
    expect(screen.getByRole('textbox', { name: 'Feature question' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: 'Send' })).toBeNull()
  })

  test('submits through a labelled form and cancels while busy', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    const onCancel = vi.fn()
    render(
      <PromptComposer
        busy
        canSubmit={false}
        onCancel={onCancel}
        onPromptChange={() => undefined}
        onSubmit={onSubmit}
        prompt="Question"
        promptLabel="Ask"
        submitLabel="Send"
      />,
    )

    const form = screen.getByRole('form', { name: 'Ask' })
    expect(form.getAttribute('aria-busy')).toBe('true')
    expect((screen.getByRole('textbox', { name: 'Ask' }) as HTMLTextAreaElement).value).toBe(
      'Question',
    )
    expect((screen.getByRole('button', { name: 'Send' }) as HTMLButtonElement).disabled).toBe(true)
    await user.click(screen.getByRole('button', { name: 'Cancel request' }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  test('forwards controlled prompt changes and form submission', () => {
    const onPromptChange = vi.fn()
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    render(
      <PromptComposer
        canSubmit
        onPromptChange={onPromptChange}
        onSubmit={onSubmit}
        prompt=""
        promptLabel="Ask a question"
        submitLabel="Send"
      />,
    )

    fireEvent.change(screen.getByRole('textbox', { name: 'Ask a question' }), {
      target: { value: 'Where is the handbook?' },
    })
    fireEvent.submit(screen.getByRole('form', { name: 'Ask a question' }))

    expect(onPromptChange).toHaveBeenCalledWith('Where is the handbook?')
    expect(onSubmit).toHaveBeenCalledTimes(1)
  })
})

describe('ChatSurface', () => {
  test('lets a feature keep one labelled transcript scroller with its ref and scroll callback', () => {
    const transcriptRef = createRef<HTMLDivElement>()
    const onScroll = vi.fn()
    const { container } = render(
      <ChatSurface
        className="feature-surface"
        composer={<div>Composer</div>}
        composerClassName="feature-composer-shell"
        label="Chat Workspace"
        transcript={<p>Transcript</p>}
        transcriptClassName="feature-transcript"
        transcriptProps={{ 'aria-busy': true, 'aria-label': 'Chat Transcript', onScroll, role: 'region' }}
        transcriptRef={transcriptRef}
      />,
    )

    const surface = screen.getByRole('region', { name: 'Chat Workspace' })
    const transcript = screen.getByRole('region', { name: 'Chat Transcript' })
    expect(surface.className).toContain('feature-surface')
    expect(transcript.className).toContain('feature-transcript')
    expect(transcript.getAttribute('aria-busy')).toBe('true')
    expect(transcriptRef.current).toBe(transcript)
    fireEvent.scroll(transcript)
    expect(onScroll).toHaveBeenCalledTimes(1)
    expect(
      container.querySelector('[data-slot="chat-composer"]')?.className,
    ).toContain('feature-composer-shell')
    expect(screen.getAllByRole('region', { name: 'Chat Transcript' })).toHaveLength(1)
  })

  test('renders the provided empty transcript with separate transcript and composer scroll regions', () => {
    const { container } = render(
      <ChatSurface
        composer={<div>Composer</div>}
        empty={<p>No conversation yet</p>}
        isEmpty
        transcript={<p>Hidden transcript</p>}
      />,
    )

    expect(screen.getByText('No conversation yet')).toBeTruthy()
    expect(screen.queryByText('Hidden transcript')).toBeNull()
    expect(container.querySelector('[data-slot="chat-transcript"]')?.className).toContain(
      'overflow-y-auto',
    )
    expect(container.querySelector('[data-slot="chat-composer"]')?.className).toContain(
      'overflow-y-auto',
    )
  })
})

describe('StreamingAnswer', () => {
  test('marks a streaming answer busy and renders source and action slots', () => {
    render(
      <StreamingAnswer
        actions={<button type="button">Copy answer</button>}
        isStreaming
        label="Answer"
        sources={<a href="#handbook">Handbook.pdf</a>}
      >
        The handbook is available in the workspace.
      </StreamingAnswer>,
    )

    const answer = screen.getByRole('article', { name: 'Answer' })
    expect(answer.getAttribute('aria-busy')).toBe('true')
    expect(answer.textContent).toContain('The handbook is available in the workspace.')
    expect(screen.getByRole('link', { name: 'Handbook.pdf' })).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Copy answer' })).toBeTruthy()
  })
})

describe('ContextChunkList', () => {
  test('opens the selected real chunk id', async () => {
    const user = userEvent.setup()
    const onOpenChunk = vi.fn()
    render(
      <ContextChunkList
        chunks={[
          {
            content: 'Evidence',
            id: 'chunk-7',
            openLabel: 'View Source Guide.pdf',
            sourceLabel: 'Guide.pdf',
          },
        ]}
        emptyLabel="No context"
        label="Retrieved context"
        onOpenChunk={onOpenChunk}
      />,
    )

    const list = screen.getByRole('list', { name: 'Retrieved context' })
    expect(list.getAttribute('data-slot')).toBe('context-chunk-list')
    expect(
      screen.queryByRole('region', { name: 'Retrieved context' }),
    ).toBeNull()
    await user.click(screen.getByRole('button', { name: 'View Source Guide.pdf' }))
    expect(onOpenChunk).toHaveBeenCalledWith('chunk-7')
  })

  test('uses its supplied empty label when there are no chunks', () => {
    render(
      <ContextChunkList
        chunks={[]}
        emptyLabel="No context"
        label="Retrieved context"
      />,
    )

    expect(screen.getByRole('status').textContent).toContain('No context')
  })

  test('wraps a long source identifier while keeping source and score discoverable', () => {
    const source = 'source-with-an-extremely-long-unbroken-identifier-that-must-wrap.md'
    render(
      <ContextChunkList
        chunks={[
          {
            content: 'Evidence',
            id: 'chunk-long',
            meta: 'Score 0.88',
            openLabel: `View Source ${source}`,
            sourceLabel: source,
          },
        ]}
        emptyLabel="No context"
        label="Retrieved context"
        onOpenChunk={() => undefined}
      />,
    )

    const sourceButton = screen.getByRole('button', {
      name: `View Source ${source}`,
    })
    expect(sourceButton.className).toContain('min-w-0')
    expect(sourceButton.className).toContain('whitespace-normal')
    expect(sourceButton.className).toContain('break-words')
    expect(sourceButton.textContent).toBe(source)
    expect(screen.getByText('Score 0.88').textContent).toBe('Score 0.88')
    expect(sourceButton.className).toContain('max-[680px]:min-h-11')
  })
})

test('bordered conversation containers retain square chrome', () => {
  const { container } = render(
    <>
      <StreamingAnswer>Answer</StreamingAnswer>
      <ChatSurface composer={<div>Composer</div>} transcript={<div>Transcript</div>} />
      <PromptComposer
        canSubmit
        onPromptChange={() => undefined}
        onSubmit={(event) => event.preventDefault()}
        prompt=""
        promptLabel="Ask"
        submitLabel="Send"
      />
      <ContextChunkList
        chunks={[{ id: 'chunk-7', content: 'Evidence', sourceLabel: 'Guide.pdf' }]}
        emptyLabel="No context"
        label="Retrieved context"
      />
    </>,
  )

  for (const selector of [
    '[data-slot="streaming-answer"]',
    '[data-slot="chat-surface"]',
    '[data-slot="prompt-composer"]',
    '[data-slot="context-chunk-list"]',
  ]) {
    expect(container.querySelector(selector)?.className).toContain('rounded-[2px]')
  }
})
