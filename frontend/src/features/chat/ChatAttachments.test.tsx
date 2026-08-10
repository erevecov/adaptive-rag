/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { afterEach, describe, expect, test, vi } from 'vitest'

afterEach(() => {
  cleanup()
})

import {
  AttachmentChips,
  MAX_CHAT_ATTACHMENTS,
  useChatAttachments,
  type ChatAttachmentUploadResponse,
} from './ChatAttachments'

function Harness({
  upload = vi.fn(async (file: File): Promise<ChatAttachmentUploadResponse> => ({
    id: `id-${file.name}`,
    kind: file.type.startsWith('image/') ? 'image' : 'document',
    filename: file.name,
    mime: file.type || 'application/octet-stream',
    size_bytes: file.size,
  })),
  maxAttachments = MAX_CHAT_ATTACHMENTS,
}: {
  upload?: (file: File) => Promise<ChatAttachmentUploadResponse>
  maxAttachments?: number
}) {
  const api = useChatAttachments({ upload, maxAttachments })
  const [blocked, setBlocked] = useState(false)
  return (
    <div>
      <button
        type="button"
        onClick={() => {
          const file = new File(['hello'], 'note.txt', { type: 'text/plain' })
          api.addFiles([file])
          setBlocked(api.blocked)
        }}
      >
        Add
      </button>
      <button
        type="button"
        onClick={() => {
          const files = Array.from({ length: 6 }, (_, index) =>
            new File([`x${index}`], `f${index}.txt`, { type: 'text/plain' }),
          )
          api.addFiles(files)
        }}
      >
        Add many
      </button>
      <span data-testid="count">{api.attachments.length}</span>
      <span data-testid="blocked">{String(api.blocked)}</span>
      <span data-testid="ready">{api.readyAttachments.length}</span>
      <span data-testid="was-blocked-on-add">{String(blocked)}</span>
      <AttachmentChips
        attachments={api.attachments.map((item) => ({
          localId: item.localId,
          filename: item.file.name,
          previewUrl: item.previewUrl,
          kind: item.kind,
          status: item.status,
          error: item.error,
        }))}
        onRemove={api.remove}
      />
    </div>
  )
}

describe('useChatAttachments', () => {
  test('uploads a file to ready and exposes remove', async () => {
    const user = userEvent.setup()
    render(<Harness />)
    await user.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => {
      expect(screen.getByTestId('ready').textContent).toBe('1')
    })
    expect(screen.getByTestId('count').textContent).toBe('1')
    expect(screen.getByTestId('blocked').textContent).toBe('false')
    await user.click(
      screen.getByRole('button', { name: 'Remove attachment note.txt' }),
    )
    expect(screen.getByTestId('count').textContent).toBe('0')
  })

  test('caps at max attachments', async () => {
    const user = userEvent.setup()
    render(<Harness maxAttachments={5} />)
    await user.click(screen.getByRole('button', { name: 'Add many' }))
    await waitFor(() => {
      expect(screen.getByTestId('count').textContent).toBe('5')
    })
  })

  test('blocks while upload fails', async () => {
    const user = userEvent.setup()
    const upload = vi.fn(async () => {
      throw new Error('nope')
    })
    render(<Harness upload={upload} />)
    await user.click(screen.getByRole('button', { name: 'Add' }))
    await waitFor(() => {
      expect(screen.getByTestId('blocked').textContent).toBe('true')
    })
    expect(screen.getByTestId('ready').textContent).toBe('0')
  })
})
