/**
 * @vitest-environment jsdom
 */
import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import type {
  ApiClient,
  UserMemory,
  UserMemoryListResponse,
} from '@/lib/apiClient'
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
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-2'))
  })

  test('offers Undo after soft-remove and restores via approve', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
    const reject = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'rejected'
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
        apiClient={createMemoryClient({ approve, list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-2'))
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Undo remove from injection' }),
    )
    await waitFor(() => expect(approve).toHaveBeenCalledWith('mem-2'))
    expect(await screen.findByText('1 Injectable')).toBeTruthy()
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
  })

  test('Esc and Dismiss clear the soft-remove Undo banner', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
      memory({ content: 'Other live', id: 'mem-3', status: 'approved' }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
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
        apiClient={createMemoryClient({ list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getAllByRole('button', { name: 'Remove from injection' })[0],
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalled())
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByRole('button', { name: 'Undo remove from injection' }),
      ),
    )
    await user.keyboard('{Escape}')
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
    await waitFor(() =>
      expect(document.activeElement).toBe(
        document.getElementById('propose-again-mem-2'),
      ),
    )

    await user.click(
      screen.getAllByRole('button', { name: 'Remove from injection' })[0],
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Dismiss undo remove' }))
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
    await waitFor(() =>
      expect(document.activeElement).toBe(
        document.getElementById('propose-again-mem-3'),
      ),
    )
  })

  test('changing status filter clears the soft-remove Undo banner', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
      memory({ content: 'Other live', id: 'mem-3', status: 'approved' }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
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
        apiClient={createMemoryClient({ list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getAllByRole('button', { name: 'Remove from injection' })[0],
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalled())
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^All/ }))
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
  })

  test('switches to Rejected when soft-remove empties the Approved filter', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
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
        apiClient={createMemoryClient({ list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Approved/ }))
    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-2'))
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()
    expect(await screen.findByRole('button', { name: /Propose Again/i })).toBeTruthy()
    const rejectedFilter = screen.getByRole('button', { name: /^Rejected/ })
    expect(rejectedFilter.getAttribute('aria-pressed')).toBe('true')
    expect(
      await screen.findByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeTruthy()
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByRole('button', { name: /Propose Again/i }),
      ),
    )
    await user.keyboard('{Escape}')
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
    expect(
      screen.queryByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeNull()
  })

  test('Undo from Rejected after empty-Approved switch returns to Approved', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
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
    const reject = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'rejected'
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
        apiClient={createMemoryClient({ approve, list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Approved/ }))
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-2'))
    expect(
      screen.getByRole('button', { name: /^Rejected/ }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      await screen.findByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Undo remove from injection' }),
    )
    await waitFor(() => expect(approve).toHaveBeenCalledWith('mem-2'))
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /^Approved/ }).getAttribute('aria-pressed'),
      ).toBe('true'),
    )
    expect(
      screen.queryByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeNull()
    expect(await screen.findByText('Live preference')).toBeTruthy()
    expect(await screen.findByText('1 Injectable')).toBeTruthy()
  })


  test('caps injectable badge at injection max_items (8)', async () => {
    const items = Array.from({ length: 10 }, (_, index) =>
      memory({
        content: `Approved preference ${index + 1}`,
        id: `mem-${index + 1}`,
        status: 'approved',
      }),
    )
    const list = vi.fn(async () => ({ items }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('8 Injectable')).toBeTruthy()
    expect(screen.queryByText('10 Injectable')).toBeNull()
    expect(screen.getByLabelText('8 injectable')).toBeTruthy()
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
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByLabelText('Propose Memory'),
      ),
    )
  })

  test('successful propose cancels pending confirm-remove', async () => {
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
    const reject = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'rejected'
      return item
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
        apiClient={createMemoryClient({ list, propose, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Approved/ }))
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-1'))
    expect(
      await screen.findByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeTruthy()
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()

    const draftField = screen.getByLabelText('Propose Memory')
    await user.click(draftField)
    await user.clear(draftField)
    await user.type(draftField, 'Replacement preference')
    await user.click(screen.getByRole('button', { name: 'Propose' }))
    await waitFor(() => expect(propose).toHaveBeenCalled())
    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: /^Proposed/ }).getAttribute('aria-pressed'),
      ).toBe('true'),
    )
    await waitFor(() =>
      expect(
        screen.queryByText(
          /Showing Rejected — soft-removed item is below with Propose Again/i,
        ),
      ).toBeNull(),
    )
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
    expect(await screen.findByText('Replacement preference')).toBeTruthy()
  })

  test('View Proposed clears soft-remove banners after rejected list failure', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Live preference', id: 'mem-1', status: 'approved' }),
    ]
    let failRejectedLoad = false
    const list = vi.fn(async (params?: { status?: string | null }) => {
      const status = params?.status ?? null
      if (failRejectedLoad && status === 'rejected') {
        throw new Error('rejected list failed')
      }
      const items =
        status === null || status === undefined
          ? [...store]
          : store.filter((item) => item.status === status)
      return { items }
    })
    const reject = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'rejected'
      failRejectedLoad = true
      return item
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: /^Approved/ }))
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    await user.click(screen.getByRole('button', { name: /Confirm remove/ }))
    await waitFor(() => expect(reject).toHaveBeenCalledWith('mem-1'))
    expect(
      await screen.findByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeTruthy()
    expect(await screen.findByText(/Removed from injection/)).toBeTruthy()
    expect(await screen.findByText(/rejected list failed/i)).toBeTruthy()
    expect(await screen.findByText('No Rejected Memories')).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'View Proposed' }))
    expect(
      screen.getByRole('button', { name: /^Proposed/ }).getAttribute('aria-pressed'),
    ).toBe('true')
    expect(
      screen.queryByText(
        /Showing Rejected — soft-removed item is below with Propose Again/i,
      ),
    ).toBeNull()
    expect(screen.queryByText(/Removed from injection/)).toBeNull()
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
    expect(await screen.findByText('No Rejected Memories')).toBeTruthy()
    expect(screen.getByText(/never inject into chat/i)).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'View Proposed' }))
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
    expect(await screen.findByText('No Approved Memories')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'View Proposed' }))
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

  test('retries a failed list load', async () => {
    const user = userEvent.setup()
    let shouldFail = true
    const list = vi.fn(async () => {
      if (shouldFail) {
        shouldFail = false
        throw new Error('temporary outage')
      }
      return {
        items: [
          memory({ content: 'Recovered note', id: 'mem-1', status: 'proposed' }),
        ],
      }
    })

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('temporary outage')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('Recovered note')).toBeTruthy()
  })

  test('saves an edit with Ctrl+Enter and shows a char counter', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Draft text', id: 'mem-1', status: 'proposed' }),
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

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list, update })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Draft text')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Edit' }))
    const editor = screen.getByLabelText('Edit Memory Content')
    expect(screen.getByText(/⌘\/Ctrl\+Enter save/)).toBeTruthy()
    await user.clear(editor)
    await user.type(editor, 'Edited via shortcut')
    editor.focus()
    await user.keyboard('{Control>}{Enter}{/Control}')
    await waitFor(() => expect(update).toHaveBeenCalled())
    expect(await screen.findByText('Edited via shortcut')).toBeTruthy()
  })

  test('Escape cancels confirm-remove and relative time exposes absolute title', async () => {
    const user = userEvent.setup()
    const recent = new Date(Date.now() - 5 * 60 * 1000).toISOString()
    const store: UserMemory[] = [
      memory({
        content: 'Live preference',
        created_at: recent,
        id: 'mem-2',
        status: 'approved',
      }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
    const reject = vi.fn()

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    const stamped = screen.getByText('5m ago')
    expect(stamped.getAttribute('datetime')).toBe(recent)
    expect(stamped.getAttribute('title')).toBeTruthy()

    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    expect(
      await screen.findByRole('button', { name: /Confirm remove/ }),
    ).toBeTruthy()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('button', { name: /Confirm remove/ })).toBeNull()
    const removeButton = screen.getByRole('button', {
      name: 'Remove from injection',
    })
    expect(removeButton).toBeTruthy()
    await waitFor(() => expect(document.activeElement).toBe(removeButton))
    expect(reject).not.toHaveBeenCalled()
  })

  test('opens an editable textarea when Edit is clicked', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Draft text', id: 'mem-1', status: 'proposed' }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Draft text')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Edit' }))
    const editor = await screen.findByLabelText('Edit Memory Content')
    expect(editor).toBeTruthy()
    expect(screen.getByText(/⌘\/Ctrl\+Enter save/)).toBeTruthy()
    await waitFor(() => expect(document.activeElement).toBe(editor))
  })

  test('lists Proposed before Approved on the All filter', async () => {
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Live preference', id: 'mem-approved', status: 'approved' }),
        memory({ content: 'Needs review', id: 'mem-proposed', status: 'proposed' }),
        memory({ content: 'Dropped', id: 'mem-rejected', status: 'rejected' }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Needs review')).toBeTruthy()
    const texts = screen.getAllByText(/Needs review|Live preference|Dropped/)
    expect(texts.map((node) => node.textContent)).toEqual([
      'Needs review',
      'Live preference',
      'Dropped',
    ])
  })

  test('shows a loading skeleton while the first list fetch is in flight', async () => {
    let resolveList: ((value: { items: UserMemory[] }) => void) | undefined
    const list = vi.fn(
      () =>
        new Promise<{ items: UserMemory[] }>((resolve) => {
          resolveList = resolve
        }),
    )

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByRole('status', { name: 'Loading Memories' })).toBeTruthy()
    expect(
      document.querySelector('[data-slot="memory-list-loading"]'),
    ).toBeTruthy()

    resolveList?.({
      items: [
        memory({ content: 'Loaded note', id: 'mem-1', status: 'proposed' }),
      ],
    })
    expect(await screen.findByText('Loaded note')).toBeTruthy()
    expect(screen.queryByRole('status', { name: 'Loading Memories' })).toBeNull()
  })

  test('shows confirm-remove guidance and Keep In Injection control', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
      ],
    }))
    const reject = vi.fn()

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    expect(
      await screen.findByText(/Confirm remove drops injection/i),
    ).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Keep In Injection' }),
    )
    expect(screen.queryByRole('button', { name: /Confirm remove/i })).toBeNull()
    expect(reject).not.toHaveBeenCalled()
  })

  test('empty Proposed filter offers Focus Propose', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async (params?: { status?: string | null }) => {
      if (params?.status === 'proposed') {
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

    await user.click(await screen.findByRole('button', { name: /^Proposed/ }))
    expect(await screen.findByText('No Proposed Memories')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Focus Propose' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByLabelText('Propose Memory'),
      ),
    )
  })

  test('empty Rejected filter offers Focus Propose beside View Proposed', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async (params?: { status?: string | null }) => {
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
    expect(await screen.findByText('No Rejected Memories')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'View Proposed' })).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Focus Propose' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByLabelText('Propose Memory'),
      ),
    )
  })

  test('marks a busy row while approve is in flight and shows refresh status', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Keyboard preference', id: 'mem-1', status: 'proposed' }),
    ]
    let releaseApprove: (() => void) | undefined
    const list = vi.fn(async () => ({ items: [...store] }))
    const approve = vi.fn(
      () =>
        new Promise<UserMemory>((resolve) => {
          releaseApprove = () => {
            store[0] = { ...store[0], status: 'approved' }
            resolve(store[0])
          }
        }),
    )

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ approve, list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Keyboard preference')).toBeTruthy()
    const approveButton = screen.getByRole('button', { name: 'Approve' })
    await user.click(approveButton)
    const row = document.getElementById('user-memory-mem-1')
    expect(row?.getAttribute('aria-busy')).toBe('true')

    releaseApprove?.()
    await waitFor(() =>
      expect(document.getElementById('user-memory-mem-1')?.getAttribute('aria-busy')).toBeNull(),
    )
  })

  test('announces injectable count after approve and Esc cancels confirm globally', async () => {
    const user = userEvent.setup()
    const store: UserMemory[] = [
      memory({ content: 'Draft note', id: 'mem-1', status: 'proposed' }),
      memory({
        content: 'Live preference',
        id: 'mem-2',
        status: 'approved',
      }),
    ]
    const list = vi.fn(async () => ({ items: [...store] }))
    const approve = vi.fn(async (id: string) => {
      const item = store.find((entry) => entry.id === id)
      if (!item) {
        throw new Error('missing')
      }
      item.status = 'approved'
      return item
    })
    const reject = vi.fn()

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ approve, list, reject })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByLabelText('1 injectable')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Approve' }))
    expect(await screen.findByLabelText('2 injectable')).toBeTruthy()

    const removeButtons = screen.getAllByRole('button', {
      name: 'Remove from injection',
    })
    await user.click(removeButtons[0])
    expect(
      await screen.findByRole('button', { name: /Confirm remove/i }),
    ).toBeTruthy()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('button', { name: /Confirm remove/i })).toBeNull()
    expect(reject).not.toHaveBeenCalled()
  })

  test('Propose Again copies rejected content into the draft field', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async () => ({
      items: [
        memory({
          content: 'Old preference worth retrying',
          id: 'mem-rej',
          status: 'rejected',
        }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Old preference worth retrying')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: /Propose Again/i }),
    )
    const draft = screen.getByLabelText('Propose Memory') as HTMLTextAreaElement
    expect(draft.value).toBe('Old preference worth retrying')
    await waitFor(() => expect(document.activeElement).toBe(draft))
  })

  test('orders newer memories first within the same status on All', async () => {
    const older = '2026-08-01T00:00:00Z'
    const newer = '2026-08-05T00:00:00Z'
    const list = vi.fn(async () => ({
      items: [
        memory({
          content: 'Older proposed',
          created_at: older,
          id: 'mem-old',
          status: 'proposed',
        }),
        memory({
          content: 'Newer proposed',
          created_at: newer,
          id: 'mem-new',
          status: 'proposed',
        }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Newer proposed')).toBeTruthy()
    const texts = screen.getAllByText(/Older proposed|Newer proposed/)
    expect(texts.map((node) => node.textContent)).toEqual([
      'Newer proposed',
      'Older proposed',
    ])
  })

  test('empty Approved filter offers Focus Propose', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async (params?: { status?: string | null }) => {
      if (params?.status === 'approved') {
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

    await user.click(await screen.findByRole('button', { name: /^Approved/ }))
    expect(await screen.findByText('No Approved Memories')).toBeTruthy()
    await user.click(screen.getByRole('button', { name: 'Focus Propose' }))
    await waitFor(() =>
      expect(document.activeElement).toBe(
        screen.getByLabelText('Propose Memory'),
      ),
    )
  })

  test('shows a Proposed badge when proposals await review', async () => {
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Needs review', id: 'mem-1', status: 'proposed' }),
        memory({ content: 'Live', id: 'mem-2', status: 'approved' }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByLabelText('1 proposed')).toBeTruthy()
    expect(screen.getByLabelText('1 injectable')).toBeTruthy()
  })

  test('Tab cycles between Confirm remove and Keep In Injection', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    const confirm = await screen.findByRole('button', {
      name: /Confirm remove/i,
    })
    expect(document.activeElement).toBe(confirm)
    await user.tab()
    expect(document.activeElement).toBe(
      screen.getByRole('button', { name: 'Keep In Injection' }),
    )
    await user.tab()
    expect(document.activeElement).toBe(confirm)
  })

  test('disables status filters while the first list load is in flight', async () => {
    let resolveList: ((value: { items: UserMemory[] }) => void) | undefined
    const list = vi.fn(
      () =>
        new Promise<{ items: UserMemory[] }>((resolve) => {
          resolveList = resolve
        }),
    )

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByRole('status', { name: 'Loading Memories' })).toBeTruthy()
    expect(
      (screen.getByRole('button', { name: /^All/ }) as HTMLButtonElement).disabled,
    ).toBe(true)

    resolveList?.({
      items: [
        memory({ content: 'Loaded note', id: 'mem-1', status: 'proposed' }),
      ],
    })
    expect(await screen.findByText('Loaded note')).toBeTruthy()
    expect(
      (screen.getByRole('button', { name: /^All/ }) as HTMLButtonElement).disabled,
    ).toBe(false)
  })

  test('announces confirm-remove guidance assertively', async () => {
    const user = userEvent.setup()
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    await user.click(
      screen.getByRole('button', { name: 'Remove from injection' }),
    )
    expect(
      await screen.findByRole('button', { name: /Confirm remove/i }),
    ).toBeTruthy()
    const hint = document.getElementById('memory-confirm-remove-hint')
    expect(hint).toBeTruthy()
    expect(hint?.getAttribute('aria-live')).toBe('assertive')
    expect(hint?.getAttribute('role')).toBe('status')
  })








  test('ignores stale refreshList responses when a newer load supersedes them', async () => {
    type Resolver = (value: UserMemoryListResponse) => void
    const pending: Resolver[] = []
    const list = vi.fn(
      () =>
        new Promise<UserMemoryListResponse>((resolve) => {
          pending.push(resolve)
        }),
    )
    const client = createMemoryClient({ list })

    const { rerender } = render(
      <UserMemoryPanel apiClient={client} projectId="project-1" />,
    )

    // Mount load for project-1 (all filter → one list call).
    await waitFor(() => expect(pending.length).toBe(1))
    await act(async () => {
      pending.shift()!({
        items: [
          memory({ content: 'Project one note', id: 'mem-1', status: 'approved' }),
        ],
      })
    })
    expect(await screen.findByText('Project one note')).toBeTruthy()

    // Start refreshList via Retry is not available — call path: change project
    // after leaving a refresh in flight. Soft path: click Retry after failure
    // is heavy. Instead bump via refreshList by using the empty-state retry is
    // only on failure. Use soft-remove? Simpler: force a second concurrent
    // list by re-rendering projectId while first refresh is outstanding.
    //
    // Kick refreshList by flipping to Rejected then back is chip-disabled while
    // loading. So: start refresh via programmatic path — list again by
    // re-rendering same project after we first hang a refreshList:
    // 1) fail load then retry hangs
    // Easiest: hang refresh by clicking Retry after a failed refresh.
    //
    // Practical path used here:
    // - re-render project-2 starts a new load (increments shared request id)
    // - resolve the OLD project-1 response afterward (if any still pending)
    // - resolve project-2 last
    //
    // To create an overlapping refreshList: first hang list on a second call.
    // After mount settled, we re-render project-2 (load starts, deferred).
    // Before resolving, we would need another refresh — actually the race is:
    // load A in flight, refreshList B starts and finishes first with stale,
    // then load A would have won without guard when B is newer...
    //
    // Desired race: older request resolves AFTER newer request started.
    // 1) project-1 mount resolved
    // 2) switch to project-2 → load starts (id=2), pending
    // 3) resolve nothing yet; switch to project-3 → load starts (id=3),
    //    cleanup invalidates id=2
    // 4) resolve id=2 payload with STALE — must not show
    // 5) resolve id=3 with FRESH — must show

    await act(async () => {
      rerender(<UserMemoryPanel apiClient={client} projectId="project-2" />)
    })
    await waitFor(() => expect(pending.length).toBe(1))
    const staleResolver = pending.shift()!

    await act(async () => {
      rerender(<UserMemoryPanel apiClient={client} projectId="project-3" />)
    })
    await waitFor(() => expect(pending.length).toBe(1))
    const freshResolver = pending.shift()!

    await act(async () => {
      staleResolver({
        items: [
          memory({
            content: 'STALE_SHOULD_NOT_SHOW',
            id: 'stale',
            status: 'approved',
          }),
        ],
      })
    })
    expect(screen.queryByText('STALE_SHOULD_NOT_SHOW')).toBeNull()

    await act(async () => {
      freshResolver({
        items: [
          memory({
            content: 'Fresh project three note',
            id: 'fresh',
            status: 'approved',
          }),
        ],
      })
    })
    expect(await screen.findByText('Fresh project three note')).toBeTruthy()
    expect(screen.queryByText('STALE_SHOULD_NOT_SHOW')).toBeNull()
  })


  test('uses denser ≤680 spacing on Memory shell and Propose form', async () => {
    const list = vi.fn(async () => ({
      items: [
        memory({ content: 'Live preference', id: 'mem-2', status: 'approved' }),
      ],
    }))

    render(
      <UserMemoryPanel
        apiClient={createMemoryClient({ list })}
        projectId="project-1"
      />,
    )

    expect(await screen.findByText('Live preference')).toBeTruthy()
    const panel = screen.getByRole('region', { name: 'Memory' })
    expect(panel.className).toContain('max-[680px]:gap-0.5')
    expect(panel.className).toContain('max-[680px]:p-0.5')
    const draft = screen.getByLabelText('Propose Memory')
    expect(draft.className).toContain('max-[680px]:min-h-14')
    const form = draft.closest('form')
    expect(form?.className).toContain('max-[680px]:gap-0.5')
    const contentStack = screen.getByText('Live preference').parentElement
    expect(contentStack?.className).toContain('max-[680px]:gap-0.5')
    const filters = screen.getByRole('group', { name: 'Memory Status Filters' })
    expect(filters.className).toContain('max-[680px]:gap-0.5')
    const filterCount = filters.querySelector('span[aria-hidden]')
    expect(filterCount?.className).toContain('max-[680px]:text-[0.5625rem]')
    const header = screen.getByRole('heading', { name: 'Memory' }).closest('header')
    expect(header?.className).toContain('max-[680px]:gap-0.5')
    const titleStack = screen.getByRole('heading', { name: 'Memory' }).parentElement
    expect(titleStack?.className).toContain('max-[680px]:gap-0.5')
    const badgeRow = screen.getByLabelText(/injectable/i).parentElement
    expect(badgeRow?.className).toContain('max-[680px]:gap-0.5')
    const badgeColumn = badgeRow?.parentElement
    expect(badgeColumn?.className).toContain('max-[680px]:gap-0.5')
  })

})
