/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import {
  ApiClientError,
  type ApiClient,
  type RetrievalSearchResponse,
} from '@/lib/apiClient'
import { installPointerEventMocks } from '@/test/pointerEvents'

import { RetrievalPlaygroundPanel } from './RetrievalPlaygroundView'

installPointerEventMocks()

afterEach(() => {
  cleanup()
})

function createClient(
  search: ApiClient['searchRetrieval'] = vi.fn(),
): ApiClient {
  return {
    searchRetrieval: search,
  } as unknown as ApiClient
}

const sampleResponse: RetrievalSearchResponse = {
  results: [
    {
      chunk_id: 'chunk-1',
      distance: 0.1,
      score: 0.92,
      strategy: 'dense_sparse',
      citation: {
        source_id: 'src-1',
        source_type: 'text',
        source_external_id: 'policy.md',
        source_tags: [],
        source_extra_metadata: null,
        document_id: 'doc-1',
        document_stable_id: 'stable-1',
        document_version_id: 'ver-1',
        document_version_number: 1,
        chunk_id: 'chunk-1',
        char_start: 0,
        char_end: 20,
        snippet: 'Refunds are available within 30 days.',
        section_metadata: null,
      },
      embedding_metadata: null,
    },
  ],
}

describe('RetrievalPlaygroundPanel', () => {
  test('searches and renders ranked results', async () => {
    const user = userEvent.setup()
    const search = vi.fn().mockResolvedValue(sampleResponse)
    render(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )

    expect(screen.getByText('Ready').getAttribute('data-slot')).toBe('badge')
    expect(screen.getByText('Ready').getAttribute('data-tone')).toBe('neutral')
    const rerankHelp = screen.getByText(/Enable Rerank to edit candidate limit/)
    expect(rerankHelp.getAttribute('data-slot')).toBe('field-help')
    expect(
      screen.getByLabelText('Rerank candidates').getAttribute('aria-describedby'),
    ).toBe('rerank-limit-help')

    await user.type(
      screen.getByLabelText('Query'),
      'What is the refund policy?',
    )
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      expect(search).toHaveBeenCalledWith('project-1', {
        query: 'What is the refund policy?',
        limit: 10,
        strategy: 'dense_sparse',
        rerank: null,
      })
    })
    expect(screen.getByText('policy.md')).toBeTruthy()
    expect(
      screen.getByText('Refunds are available within 30 days.'),
    ).toBeTruthy()
    expect(screen.getByText('0.9200')).toBeTruthy()
    const rankBadge = screen.getByLabelText('Rank 1')
    expect(rankBadge.className).toMatch(/tabular-nums/)
    expect(rankBadge.closest('[data-rank="1"]')).toBeTruthy()
    expect(screen.getByLabelText('Score 0.9200').className).toMatch(
      /tabular-nums/,
    )
    const doneBadge = screen.getByText('Done')
    expect(doneBadge.getAttribute('data-slot')).toBe('badge')
    expect(doneBadge.getAttribute('data-tone')).toBe('success')
    expect(screen.getAllByText('Dense + Sparse (Default)').length).toBeGreaterThan(0)
    expect(screen.getByText('Text')).toBeTruthy()
  })

  test('requires project and non-empty query', async () => {
    const user = userEvent.setup()
    const search = vi.fn()
    const { rerender } = render(
      <RetrievalPlaygroundPanel client={createClient(search)} projectId="" />,
    )

    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(screen.getByText(/Select a Project Before Searching/i)).toBeTruthy()
    expect(search).not.toHaveBeenCalled()
    const failedBadge = screen.getByText('Failed')
    expect(failedBadge.getAttribute('data-slot')).toBe('badge')
    expect(failedBadge.getAttribute('data-tone')).toBe('danger')

    rerender(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )
    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(screen.getByText(/non-empty query/i)).toBeTruthy()
    expect(search).not.toHaveBeenCalled()
  })

  test('surfaces API errors', async () => {
    const user = userEvent.setup()
    const search = vi.fn().mockRejectedValue(
      new ApiClientError('budget', { detail: 'graph not ready', status: 422 }),
    )
    render(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )
    await user.type(screen.getByLabelText('Query'), 'graph query')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => {
      expect(screen.getByText('graph not ready')).toBeTruthy()
    })
    const failedBadge = screen.getByText('Failed')
    expect(failedBadge.getAttribute('data-tone')).toBe('danger')
  })

  test('shows Searching badge while request is in flight', async () => {
    const user = userEvent.setup()
    let resolveSearch!: (value: RetrievalSearchResponse) => void
    const search = vi.fn(
      () =>
        new Promise<RetrievalSearchResponse>((resolve) => {
          resolveSearch = resolve
        }),
    )
    render(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )

    await user.type(screen.getByLabelText('Query'), 'in flight')
    await user.click(screen.getByRole('button', { name: 'Search' }))

    await waitFor(() => {
      const badge = screen.getByText('Searching')
      expect(badge.getAttribute('data-slot')).toBe('badge')
      expect(badge.getAttribute('data-tone')).toBe('warning')
    })
    expect(
      document.querySelector('[data-slot-state="loading"]'),
    ).toBeTruthy()

    resolveSearch(sampleResponse)
    await waitFor(() => {
      expect(screen.getByText('Done')).toBeTruthy()
    })
  })

  test('shows idle empty and clears stale results on validation failure', async () => {
    const user = userEvent.setup()
    const search = vi.fn().mockResolvedValue(sampleResponse)
    render(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )

    expect(screen.getByText(/Run a query to inspect ranked chunks/)).toBeTruthy()

    await user.type(screen.getByLabelText('Query'), 'refund')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => {
      expect(screen.getByText('#1')).toBeTruthy()
    })

    await user.clear(screen.getByLabelText('Query'))
    await user.click(screen.getByRole('button', { name: 'Search' }))
    const failed = screen.getByRole('alert')
    expect(failed.textContent).toMatch(/non-empty query/i)
    expect(
      document.querySelector(
        '[aria-label="Retrieval Results"] [data-slot-state="failed"]',
      ),
    ).toBeTruthy()
    expect(screen.queryByText('#1')).toBeNull()
  })

  test('keeps API failure inside the results region', async () => {
    const user = userEvent.setup()
    const search = vi.fn().mockRejectedValue(
      new ApiClientError('budget', { detail: 'graph not ready', status: 422 }),
    )
    render(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )
    await user.type(screen.getByLabelText('Query'), 'graph query')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => {
      expect(
        document.querySelector(
          '[aria-label="Retrieval Results"] [data-slot-state="failed"]',
        ),
      ).toBeTruthy()
    })
    expect(screen.getByText('graph not ready')).toBeTruthy()
  })

  test('redacts secrets from retrieval API failure copy', async () => {
    const user = userEvent.setup()
    const search = vi.fn().mockRejectedValue(
      new ApiClientError('unauthorized', {
        detail: 'failed with sk-abcdefghijklmnop',
        status: 401,
      }),
    )
    render(
      <RetrievalPlaygroundPanel
        client={createClient(search)}
        projectId="project-1"
      />,
    )
    await user.type(screen.getByLabelText('Query'), 'secret leak')
    await user.click(screen.getByRole('button', { name: 'Search' }))
    await waitFor(() => {
      expect(screen.getByText(/\[redacted\]/)).toBeTruthy()
    })
    expect(screen.queryByText(/sk-abcdefghijklmnop/)).toBeNull()
  })
})
