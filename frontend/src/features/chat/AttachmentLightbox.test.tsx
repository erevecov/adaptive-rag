/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { AttachmentLightbox } from './AttachmentLightbox'

afterEach(() => {
  cleanup()
})

describe('AttachmentLightbox', () => {
  test('shows local image preview and closes on Escape', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    const previewUrl = 'blob:http://localhost/fake-preview'
    render(
      <AttachmentLightbox
        item={{
          id: 'local-1',
          filename: 'shot.png',
          kind: 'image',
          mime: 'image/png',
          previewUrl,
        }}
        onClose={onClose}
      />,
    )

    const image = screen.getByRole('img', { name: 'shot.png' })
    expect(image.getAttribute('src')).toBe(previewUrl)
    expect(screen.getByRole('dialog')).toBeTruthy()

    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  test('loads remote text content via loadContent', async () => {
    const loadContent = vi.fn(async () => new Blob(['hello doc'], { type: 'text/plain' }))
    render(
      <AttachmentLightbox
        item={{
          id: 'att-1',
          filename: 'notes.txt',
          kind: 'document',
          mime: 'text/plain',
        }}
        loadContent={loadContent}
        onClose={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('hello doc')).toBeTruthy()
    })
    expect(loadContent).toHaveBeenCalledWith('att-1')
  })

  test('shows error when remote load fails', async () => {
    render(
      <AttachmentLightbox
        item={{
          id: 'att-2',
          filename: 'missing.png',
          kind: 'image',
          mime: 'image/png',
        }}
        loadContent={async () => {
          throw new Error('Attachment not found.')
        }}
        onClose={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(/Attachment not found/)
    })
  })
})
