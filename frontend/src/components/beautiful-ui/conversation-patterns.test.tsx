/**
 * @vitest-environment jsdom
 */
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
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
        sources={<a href="#handbook">Handbook.pdf</a>}
      >
        The handbook is available in the workspace.
      </StreamingAnswer>,
    )

    const answer = screen.getByRole('article')
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
        chunks={[{ id: 'chunk-7', content: 'Evidence', sourceLabel: 'Guide.pdf' }]}
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
    await user.click(screen.getByRole('button', { name: /Guide.pdf/ }))
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
