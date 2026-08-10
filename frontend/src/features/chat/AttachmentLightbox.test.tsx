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
        items={[
          {
            id: 'local-1',
            filename: 'shot.png',
            kind: 'image',
            mime: 'image/png',
            previewUrl,
          },
        ]}
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
    const loadContent = vi.fn(
      async () => new Blob(['hello doc'], { type: 'text/plain' }),
    )
    render(
      <AttachmentLightbox
        items={[
          {
            id: 'att-1',
            filename: 'notes.txt',
            kind: 'document',
            mime: 'text/plain',
          },
        ]}
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
        items={[
          {
            id: 'att-2',
            filename: 'missing.png',
            kind: 'image',
            mime: 'image/png',
          },
        ]}
        loadContent={async () => {
          throw new Error('Attachment not found.')
        }}
        onClose={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toMatch(
        /Attachment not found/,
      )
    })
  })

  test('navigates between multiple attachments with arrows and keyboard', async () => {
    const user = userEvent.setup()
    const loadContent = vi.fn(async (id: string) => {
      if (id === 'a') {
        return new Blob(['first'], { type: 'text/plain' })
      }
      if (id === 'b') {
        return new Blob(['second'], { type: 'text/plain' })
      }
      return new Blob(['third'], { type: 'text/plain' })
    })

    render(
      <AttachmentLightbox
        initialIndex={0}
        items={[
          {
            id: 'a',
            filename: 'one.txt',
            kind: 'document',
            mime: 'text/plain',
          },
          {
            id: 'b',
            filename: 'two.txt',
            kind: 'document',
            mime: 'text/plain',
          },
          {
            id: 'c',
            filename: 'three.txt',
            kind: 'document',
            mime: 'text/plain',
          },
        ]}
        loadContent={loadContent}
        onClose={vi.fn()}
      />,
    )

    await waitFor(() => {
      expect(screen.getByText('first')).toBeTruthy()
    })
    expect(screen.getByText('1 / 3')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'one.txt' })).toBeTruthy()

    await user.click(screen.getByRole('button', { name: 'Next attachment' }))
    await waitFor(() => {
      expect(screen.getByText('second')).toBeTruthy()
    })
    expect(screen.getByText('2 / 3')).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'two.txt' })).toBeTruthy()

    await user.keyboard('{ArrowRight}')
    await waitFor(() => {
      expect(screen.getByText('third')).toBeTruthy()
    })
    expect(screen.getByText('3 / 3')).toBeTruthy()

    await user.click(
      screen.getByRole('button', { name: 'Previous attachment' }),
    )
    await waitFor(() => {
      expect(screen.getByText('second')).toBeTruthy()
    })
    expect(screen.getByText('2 / 3')).toBeTruthy()

    // Wrap-around: previous from first → last
    await user.keyboard('{ArrowLeft}')
    await user.keyboard('{ArrowLeft}')
    await waitFor(() => {
      expect(screen.getByText('third')).toBeTruthy()
    })
    expect(screen.getByText('3 / 3')).toBeTruthy()
  })

  test('hides nav arrows when only one attachment', () => {
    render(
      <AttachmentLightbox
        items={[
          {
            id: 'solo',
            filename: 'only.png',
            kind: 'image',
            mime: 'image/png',
            previewUrl: 'blob:http://localhost/solo',
          },
        ]}
        onClose={vi.fn()}
      />,
    )

    expect(
      screen.queryByRole('button', { name: 'Next attachment' }),
    ).toBeNull()
    expect(
      screen.queryByRole('button', { name: 'Previous attachment' }),
    ).toBeNull()
    expect(screen.queryByText(/\/ 1/)).toBeNull()
  })
})
