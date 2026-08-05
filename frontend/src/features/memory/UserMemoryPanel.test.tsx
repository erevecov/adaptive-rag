/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type { ApiClient, UserMemory } from '@/lib/apiClient'
import { UserMemoryPanel } from './UserMemoryPanel'

afterEach(() => {
  cleanup()
})

function memory(partial: Partial<UserMemory> & Pick<UserMemory, 'id' | 'content' | 'status'>): UserMemory {
  return {
    created_at: '2026-08-05T00:00:00Z',
    project_id: null,
    reviewed_at: null,
    reviewed_by_user_id: null,
    user_id: 'user-1',
    ...partial,
  }
}

function createMemoryClient(options: {
  items?: UserMemory[]
  list?: ApiClient['listUserMemories']
  propose?: ApiClient['proposeUserMemory']
  approve?: ApiClient['approveUserMemory']
  reject?: ApiClient['rejectUserMemory']
  update?: ApiClient['updateUserMemory']
}): ApiClient {
  const items = options.items ?? []
  return {
    listUserMemories:
      options.list ??
      vi.fn(async () => ({ items: [...items] })),
    proposeUserMemory: options.propose ?? vi.fn(),
    approveUserMemory: options.approve ?? vi.fn(),
    rejectUserMemory: options.reject ?? vi.fn(),
    updateUserMemory: options.update ?? vi.fn(),
  } as unknown as ApiClient
}

describe('UserMemoryPanel', () => {
  test('lists memories and supports propose then approve', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({
        content: 'Existing proposed note',
        id: 'mem-1',
        status: 'proposed',
      }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
    const propose = vi.fn(async (body: { content: string }) => {
      const item = memory({
        content: body.content,
        id: 'mem-2',
        status: 'proposed',
      })
      store.push(item)
      return item
    })
    const approve = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'approved'
      return item
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ approve, list, propose })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Existing proposed note')).toBeTruthy()
    expect(screen.getByText(/Only approved items inject/i)).toBeTruthy()

    await user.type(
      screen.getByLabelText('Propose Memory'),
      'Prefer Spanish answers',
    )
    await user.click(screen.getByRole('button', { name: 'Propose' }))
    await waitFor(() => expect(propose).toHaveBeenCalled())
    expect(await screen.findByText('Prefer Spanish answers')).toBeTruthy()

    const approveButtons = screen.getAllByRole('button', { name: 'Approve' })
    await user.click(approveButtons[0])
    await waitFor(() => expect(approve).toHaveBeenCalled())
  })

  test('shows empty and error states', async () => {
    const list = vi.fn(async () => {
      throw new Error('boom')
    })
    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId=""
      />,
    )
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.getByText('boom')).toBeTruthy()
  })

  test('edits proposed content and removes approved from injection', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Draft text', id: 'mem-1', status: 'proposed' }),
      memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
    const update = vi.fn(async (id: string, body: { content: string }) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.content = body.content
      return item
    })
    const reject = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'rejected'
      return item
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list, reject, update })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Draft text')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Edit' }))
    const editor = screen.getByLabelText('Edit Memory Content')
    await user.clear(editor)
    await user.type(editor, 'Edited draft')
    await user.click(screen.getByRole('button', { name: 'Save' }))
    await waitFor(() => expect(update).toHaveBeenCalled())

    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-2'))
  })

  test('badge reports approved injectable count even on Proposed filter', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Draft', id: 'mem-1', status: 'proposed' }),
      memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
    ]
    const list = vi.fn(async (params?: { status?: string | null }) => {
      const status = params?.status ?? null
      const items =
        status === null || status === undefined
          ? [...store]
          : store.filter((item) => item.status === status)
      return { items }
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('1 Injectable')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Proposed/ }))
    expect(await screen.findByText('Draft')).toBeTruthy()
    expect(screen.getByText('1 Injectable')).toBeTruthy()
    expect(screen.queryByText('0 Injectable')).toBeNull()
  })

  test('switches to Proposed filter after a successful propose', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Live preference', id: 'mem-1', status: 'approved' }),
    ]
    const list = vi.fn(async (params?: { status?: string | null }) => {
      const status = params?.status ?? null
      const items =
        status === null || status === undefined
          ? [...store]
          : store.filter((item) => item.status === status)
      return { items }
    })
    const propose = vi.fn(async (body: { content: string }) => {
      const item = memory({
        content: body.content,
        id: 'mem-2',
        status: 'proposed',
      })
      store.push(item)
      return item
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list, propose })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Approved/ }))
    expect(await screen.findByText('Live preference')).toBeTruthy()

    await user.type(
      screen.getByLabelText('Propose Memory'),
      'New preference',
    )
    await user.click(screen.getByRole('button', { name: 'Propose' }))
    expect(await screen.findByText('New preference')).toBeTruthy()
    expect(
      screen.getByRole('button', { name: /^Proposed/ }).getAttribute('aria-pressed'),
    ).toBe('true')
  })


  test('shows rejected empty state with a path back to Proposed', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async (params?: { status?: string | null }) => {
      if (params?.status === 'approved') {
        return { items: [] }
      }
      if (params?.status === 'rejected') {
        return { items: [] }
      }
      return { items: [] }
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    await user.click(await screen.findByRole('button', { name: /^Rejected/ }))
    expect(await screen.findByText('No rejected memories')).toBeTruthy()
    expect(screen.getByText(/never inject into chat/i)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'View proposed' }))
    expect(
      screen.getByRole('button', { name: /^Proposed/ }).getAttribute('aria-pressed'),
    ).toBe('true')
  })

  test('approves a focused proposed row with Enter', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Keyboard preference', id: 'mem-1', status: 'proposed' }),
    ]
    const list = vi.fn(async (params?: { status?: string | null }) => {
      const status = params?.status ?? null
      const items =
        status === null || status === undefined
          ? [...store]
          : store.filter((item) => item.status === status)
      return { items }
    })
    const approve = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'approved'
      return item
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ approve, list })}
        projectId="project-1"
      />,
    )

    const row = await screen.findByLabelText(/proposed memory/i)
    row.focus()
    await user.keyboard('{Enter}')
    await waitFor(() => expect(approve).toHaveBeenCalledWith('mem-1'))
  })


  test('shows Title Case status badges and approved empty CTA', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Draft note', id: 'mem-1', status: 'proposed' }),
    ]
    const list = vi.fn(async (params?: { status?: string | null }) => {
      const status = params?.status ?? null
      if (status === 'approved') {
        return { items: [] }
      }
      const items =
        status === null || status === undefined
          ? [...store]
          : store.filter((item) => item.status === status)
      return { items }
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByLabelText(/Proposed memory/i)).toBeTruthy()
    expect(screen.getByText(/Focus a proposed row/i)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Approved/ }))
    expect(await screen.findByText('No approved memories')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'View proposed' }))
    expect(
      screen.getByRole('button', { name: /^Proposed/ }).getAttribute('aria-pressed'),
    ).toBe('true')
  })


  test('shows relative created time on memory rows', async () => {
    const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    const list = vi.fn(async (params?: { status?: string | null }) => {
      if (params?.status === 'approved') {
        return { items: [] }
      }
      return {
        items: [
          memory({
            content: 'Timed preference',
            created_at: recent,
            id: 'mem-1',
            status: 'proposed',
          }),
        ],
      }
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Timed preference')).toBeTruthy()
    expect(screen.getByText('5m ago')).toBeTruthy()
  })


  test('toggles Show more for long memory content', async () => {
    const user = userEvent.setup()
    const longContent = 'Prefer concise answers. '.repeat(20).trim()
    const list = vi.fn(async (params?: { status?: string | null }) => {
      if (params?.status === 'approved') {
        return { items: [] }
      }
      return {
        items: [
          memory({
            content: longContent,
            id: 'mem-long',
            status: 'proposed',
          }),
        ],
      }
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByRole('button', { name: 'Show more' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Show more' }))
    expect(screen.getByRole('button', { name: 'Show less' })).toBeTruthy()
  })

})
