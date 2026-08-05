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
  })

  test('requires project and non-empty query', async () => {
    const user = userEvent.setup()
    const search = vi.fn()
    const { rerender } = render(
      <RetrievalPlaygroundPanel client={createClient(search)} projectId="" />,
    )

    await user.click(screen.getByRole('button', { name: 'Search' }))
    expect(screen.getByText(/Select a project before searching/i)).toBeTruthy()
    expect(search).not.toHaveBeenCalled()

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
  })
})
