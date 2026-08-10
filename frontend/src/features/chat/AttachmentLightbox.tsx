import { useEffect, useRef, useState } from 'react'
import { Download, FileText, X } from 'lucide-react'

import { Button, IconButton } from '@/components/ui/button'
import { InlineFeedback } from '@/components/ui/feedback'
import { useFocusTrap } from '@/lib/focusTrap'
import { cn } from '@/lib/utils'

/** Item openable in the attachment lightbox (composer or transcript). */
export type AttachmentLightboxItem = {
  id: string
  filename: string
  kind: string
  mime: string
  /** When set (composer local file), skip remote fetch. */
  previewUrl?: string | null
}

type RemoteLoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; objectUrl: string | null; textContent: string | null }
  | { status: 'failed'; error: string }

export function AttachmentLightbox({
  item,
  loadContent,
  onClose,
}: {
  item: AttachmentLightboxItem
  /** Authenticated fetch for remote attachments (transcript history). */
  loadContent?(attachmentId: string): Promise<Blob>
  onClose(): void
}) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const ownedUrlRef = useRef<string | null>(null)
  const localPreview = item.previewUrl?.trim() ?? ''
  const hasLocalPreview = localPreview.length > 0

  const [localText, setLocalText] = useState<string | null>(null)
  const [remote, setRemote] = useState<RemoteLoadState>({ status: 'idle' })

  useFocusTrap(dialogRef, true)

  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape' && !event.defaultPrevented) {
        event.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  // Local text/markdown: read blob URL asynchronously (no sync setState).
  useEffect(() => {
    if (!hasLocalPreview || !isTextLikeMime(item.mime)) {
      return
    }
    let cancelled = false
    void fetch(localPreview)
      .then((response) => response.text())
      .then((text) => {
        if (!cancelled) {
          setLocalText(text)
        }
      })
      .catch(() => {
        /* image path still works via localPreview */
      })
    return () => {
      cancelled = true
    }
  }, [hasLocalPreview, item.mime, localPreview])

  // Remote content: load once when the lightbox opens without a local preview.
  useEffect(() => {
    if (hasLocalPreview) {
      return
    }
    if (loadContent === undefined) {
      // Defer setState out of the synchronous effect body.
      const timer = window.setTimeout(() => {
        setRemote({
          status: 'failed',
          error: 'Attachment preview is not available.',
        })
      }, 0)
      return () => window.clearTimeout(timer)
    }

    let cancelled = false
    const timer = window.setTimeout(() => {
      setRemote({ status: 'loading' })
      void loadContent(item.id)
        .then(async (blob) => {
          if (cancelled) {
            return
          }
          if (isTextLikeMime(item.mime) || isTextLikeMime(blob.type)) {
            const text = await blob.text()
            if (cancelled) {
              return
            }
            setRemote({ status: 'ready', objectUrl: null, textContent: text })
            return
          }
          const url = URL.createObjectURL(blob)
          if (ownedUrlRef.current !== null) {
            URL.revokeObjectURL(ownedUrlRef.current)
          }
          ownedUrlRef.current = url
          setRemote({ status: 'ready', objectUrl: url, textContent: null })
        })
        .catch((err: unknown) => {
          if (cancelled) {
            return
          }
          setRemote({
            status: 'failed',
            error:
              err instanceof Error ? err.message : 'Failed to load attachment.',
          })
        })
    }, 0)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [hasLocalPreview, item.id, item.mime, loadContent])

  useEffect(() => {
    return () => {
      if (ownedUrlRef.current !== null) {
        URL.revokeObjectURL(ownedUrlRef.current)
        ownedUrlRef.current = null
      }
    }
  }, [])

  const objectUrl = hasLocalPreview
    ? localPreview
    : remote.status === 'ready'
      ? remote.objectUrl
      : null
  const textContent = hasLocalPreview
    ? localText
    : remote.status === 'ready'
      ? remote.textContent
      : null
  const isLoading = !hasLocalPreview && remote.status === 'loading'
  const isFailed =
    !hasLocalPreview &&
    (remote.status === 'failed' ||
      (remote.status === 'idle' && loadContent === undefined))
  const errorMessage =
    remote.status === 'failed' ? remote.error : 'Attachment preview is not available.'
  const isReady =
    hasLocalPreview || remote.status === 'ready' || (hasLocalPreview && true)

  const isImage = item.kind === 'image' || item.mime.startsWith('image/')
  const isPdf =
    item.mime === 'application/pdf' ||
    item.filename.toLowerCase().endsWith('.pdf')
  const showText = textContent !== null

  return (
    <div
      aria-labelledby="attachment-lightbox-title"
      aria-modal="true"
      className="fixed inset-0 z-[80] flex items-center justify-center bg-black/70 p-4 max-[680px]:p-2"
      data-slot="attachment-lightbox"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
      role="dialog"
    >
      <div
        className={cn(
          'relative grid max-h-[min(92vh,900px)] w-full max-w-4xl grid-rows-[auto_minmax(0,1fr)]',
          'overflow-hidden rounded-lg border border-border bg-background shadow-[var(--shadow-inspector-overlay)]',
        )}
        ref={dialogRef}
      >
        <header className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
          <div className="flex min-w-0 items-center gap-2">
            <FileText
              aria-hidden="true"
              className="size-4 shrink-0 text-muted-foreground"
            />
            <h2
              className="truncate text-sm font-semibold text-foreground"
              id="attachment-lightbox-title"
              title={item.filename}
            >
              {item.filename}
            </h2>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {objectUrl !== null ? (
              <Button
                className="h-8 gap-1 px-2 text-xs"
                onClick={() => {
                  const anchor = document.createElement('a')
                  anchor.href = objectUrl
                  anchor.download = item.filename
                  anchor.rel = 'noopener'
                  anchor.click()
                }}
                size="sm"
                type="button"
                variant="ghost"
              >
                <Download aria-hidden="true" className="size-3.5" />
                Download
              </Button>
            ) : null}
            <IconButton
              label="Close attachment preview"
              onClick={onClose}
              ref={closeButtonRef}
              variant="ghost"
            >
              <X aria-hidden="true" className="size-4" />
            </IconButton>
          </div>
        </header>
        <div className="min-h-0 overflow-auto p-3 max-[680px]:p-2">
          {isLoading ? (
            <p
              aria-busy="true"
              className="text-sm text-muted-foreground"
              data-slot="attachment-lightbox-loading"
              role="status"
            >
              Loading attachment…
            </p>
          ) : null}
          {isFailed ? (
            <InlineFeedback role="alert" tone="danger">
              {errorMessage}
            </InlineFeedback>
          ) : null}
          {isReady && isImage && objectUrl !== null ? (
            <img
              alt={item.filename}
              className="mx-auto max-h-[min(80vh,800px)] max-w-full object-contain"
              data-slot="attachment-lightbox-image"
              src={objectUrl}
            />
          ) : null}
          {isReady && isPdf && objectUrl !== null ? (
            <iframe
              className="h-[min(75vh,720px)] w-full rounded-md border border-border"
              data-slot="attachment-lightbox-pdf"
              src={objectUrl}
              title={item.filename}
            />
          ) : null}
          {isReady && showText ? (
            <pre
              className="max-h-[min(75vh,720px)] overflow-auto whitespace-pre-wrap break-words rounded-md border border-border bg-muted/20 p-3 text-xs leading-relaxed text-foreground"
              data-slot="attachment-lightbox-text"
            >
              {textContent}
            </pre>
          ) : null}
          {isReady &&
          !isImage &&
          !isPdf &&
          !showText &&
          objectUrl !== null ? (
            <div
              className="grid gap-3 p-2 text-sm text-muted-foreground"
              data-slot="attachment-lightbox-binary"
            >
              <p>
                Preview is not available for this file type in the browser.
                Download it to open locally.
              </p>
              <Button
                className="w-fit gap-1"
                onClick={() => {
                  const anchor = document.createElement('a')
                  anchor.href = objectUrl
                  anchor.download = item.filename
                  anchor.rel = 'noopener'
                  anchor.click()
                }}
                type="button"
                variant="secondary"
              >
                <Download aria-hidden="true" className="size-3.5" />
                Download {item.filename}
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}

function isTextLikeMime(mime: string): boolean {
  const normalized = mime.trim().toLowerCase()
  return (
    normalized.startsWith('text/') ||
    normalized === 'application/json' ||
    normalized === 'application/xml' ||
    normalized.endsWith('+json') ||
    normalized.endsWith('+xml')
  )
}
