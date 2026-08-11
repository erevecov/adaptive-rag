/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { RetrievalResult } from '@/lib/apiClient'

import { MarkdownAnswer } from './MarkdownAnswer'

afterEach(() => {
  cleanup()
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: undefined,
  })
})

const citation = (chunkId: string, sourceId = 'source-1'): RetrievalResult => ({
  chunk_id: chunkId,
  distance: 0.1,
  score: 0.9,
  citation: {
    char_end: 10,
    char_start: 0,
    chunk_id: chunkId,
    document_id: 'document-1',
    document_stable_id: 'stable',
    document_version_id: 'version-1',
    document_version_number: 1,
    section_metadata: null,
    snippet: 'snippet',
    source_external_id: 'notes.md',
    source_extra_metadata: null,
    source_id: sourceId,
    source_tags: [],
    source_type: 'markdown',
  },
  embedding_metadata: null,
})

describe('MarkdownAnswer', () => {
  test('copies fenced code exactly through the CodeStream action', async () => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })

    render(
      <MarkdownAnswer>
        {'Before\n\n```ts\nconst answer = 42\nreturn answer\n```\n\nAfter'}
      </MarkdownAnswer>,
    )

    const code = screen.getByLabelText('Code')
    expect(code.closest('[data-slot="code-stream"]')).toBeTruthy()
    expect(
      code.closest('[data-slot="markdown-code-block"]')?.className,
    ).toContain('mb-2')
    expect(screen.getByText('Before')).toBeTruthy()
    expect(screen.getByText('After')).toBeTruthy()

    await user.click(
      within(code.closest('[data-slot="code-stream"]')!).getByRole('button', {
        name: 'Copy code',
      }),
    )
    expect(writeText).toHaveBeenCalledWith('const answer = 42\nreturn answer')
    expect((await screen.findByRole('status')).textContent).toBe(
      'Code copied to clipboard.',
    )
  })

  test('disables fenced-code copy when the Clipboard API is unavailable', () => {
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: undefined,
    })

    render(<MarkdownAnswer>{'```ts\nconst answer = 42\n```'}</MarkdownAnswer>)

    const copyButton = screen.getByRole('button', { name: 'Copy code' })
    expect((copyButton as HTMLButtonElement).disabled).toBe(true)
    expect(screen.queryByRole('status')).toBeNull()
  })

  test('reports clipboard rejection without exposing error details', async () => {
    const user = userEvent.setup()
    const writeText = vi
      .fn()
      .mockRejectedValue(new Error('Denied Bearer sk-review-secret'))
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })

    render(<MarkdownAnswer>{'```ts\nconst answer = 42\n```'}</MarkdownAnswer>)

    await user.click(screen.getByRole('button', { name: 'Copy code' }))

    expect(writeText).toHaveBeenCalledWith('const answer = 42')
    const status = await screen.findByRole('status')
    expect(status.textContent).toBe('Code could not be copied.')
    expect(status.textContent).not.toContain('sk-review-secret')
    expect(document.body.textContent).not.toContain('sk-review-secret')
  })

  test.each([
    { markdown: '```ts', name: 'an open language fence', language: 'ts' },
    { markdown: '```', name: 'a bare opening backtick fence', language: null },
    { markdown: '~~~', name: 'a bare opening tilde fence', language: null },
    { markdown: '```\n```', name: 'an empty closed fence', language: null },
  ])('copies empty code for $name without rendering undefined', async ({
    language,
    markdown,
  }) => {
    const user = userEvent.setup()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })

    render(<MarkdownAnswer>{markdown}</MarkdownAnswer>)

    const code = screen.getByLabelText('Code')
    expect(code.closest('[data-slot="code-stream"]')).toBeTruthy()
    expect(screen.queryByText('undefined')).toBeNull()
    if (language !== null) {
      expect(screen.getByText(language)).toBeTruthy()
    }

    await user.click(screen.getByRole('button', { name: 'Copy code' }))
    expect(writeText).toHaveBeenCalledTimes(1)
    expect(writeText).toHaveBeenCalledWith('')
  })

  test('keeps multiline CommonMark inline code inline without a copy action', () => {
    const { container } = render(
      <MarkdownAnswer>{'Before `line one\nline two` after'}</MarkdownAnswer>,
    )

    const inlineCode = screen.getByText('line one line two')
    expect(inlineCode.tagName).toBe('CODE')
    expect(inlineCode.closest('p')).not.toBeNull()
    expect(container.querySelector('[data-slot="code-stream"]')).toBeNull()
    expect(screen.queryByRole('button', { name: 'Copy code' })).toBeNull()
  })

  test('renders [doc-N] and [N] as beflow-style doc-N chips', async () => {
    const user = userEvent.setup()
    const onCitationClick = vi.fn()
    render(
      <MarkdownAnswer onCitationClick={onCitationClick}>
        {'Claim A [doc-1] and claim B [2].'}
      </MarkdownAnswer>,
    )
    const doc1 = screen.getByRole('button', { name: 'doc-1' })
    const doc2 = screen.getByRole('button', { name: 'doc-2' })
    expect(doc1.textContent).toBe('doc-1')
    expect(doc2.textContent).toBe('doc-2')
    expect(doc1.className).toMatch(/border-border/)
    expect(doc1.className).toMatch(/rounded-sm/)
    expect(doc1.className).not.toMatch(/rounded-full/)
    await user.click(doc1)
    await user.click(doc2)
    expect(onCitationClick).toHaveBeenNthCalledWith(1, 1)
    expect(onCitationClick).toHaveBeenNthCalledWith(2, 2)
  })

  test('maps bracketed chunk UUIDs to doc-N chips via citations', async () => {
    const user = userEvent.setup()
    const onCitationClick = vi.fn()
    const idA = 'b102a894-5215-4a35-ae80-647b5872b172'
    const idB = 'bac1c5ad-e13a-400b-b1ab-63819cf6d5c5'
    render(
      <MarkdownAnswer
        citations={[citation(idA), citation(idB)]}
        onCitationClick={onCitationClick}
      >
        {`Orion Chat Lab [${idA}][${idB}].`}
      </MarkdownAnswer>,
    )
    expect(screen.queryByText(new RegExp(idA, 'i'))).toBeNull()
    expect(screen.getByRole('button', { name: 'doc-1' }).textContent).toBe(
      'doc-1',
    )
    expect(screen.getByRole('button', { name: 'doc-2' }).textContent).toBe(
      'doc-2',
    )
    await user.click(screen.getByRole('button', { name: 'doc-1' }))
    expect(onCitationClick).toHaveBeenCalledWith(1)
  })

  test('drops unknown bracketed UUIDs instead of showing them raw', () => {
    render(
      <MarkdownAnswer citations={[citation('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')]}>
        {'Hello [bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb] world.'}
      </MarkdownAnswer>,
    )
    expect(screen.queryByText(/bbbbbbbb/i)).toBeNull()
    expect(screen.getByText(/Hello/)).toBeTruthy()
    expect(screen.getByText(/world/)).toBeTruthy()
  })
})
