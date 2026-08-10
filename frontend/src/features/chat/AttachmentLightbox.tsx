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
  const [objectUrl, setObjectUrl] = useState<string | null>(
    item.previewUrl ?? null,
  )
  const [textContent, setTextContent] = useState<string | null>(null)
  const [state, setState] = useState<'loading' | 'ready' | 'failed'>(
    item.previewUrl ? 'ready' : 'loading',
  )
  const [error, setError] = useState<string | null>(null)
  const ownedUrlRef = useRef<string | null>(null)

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

  useEffect(() => {
    let cancelled = false
    const localPreview = item.previewUrl?.trim() ?? ''
    if (localPreview.length > 0) {
      setObjectUrl(localPreview)
      setState('ready')
      setError(null)
      // Load text for local text files so docs are readable.
      if (isTextLikeMime(item.mime) && loadContent === undefined) {
        // previewUrl alone is enough for images; text needs blob read if File
        // was not passed — leave image/doc-with-preview as URL-only.
        return
      }
      if (isTextLikeMime(item.mime)) {
        void fetch(localPreview)
          .then((response) => response.text())
          .then((text) => {
            if (!cancelled) {
              setTextContent(text)
            }
          })
          .catch(() => {
            /* image path still works via objectUrl */
          })
      }
      return
    }

    if (loadContent === undefined) {
      setState('failed')
      setError('Attachment preview is not available.')
      return
    }

    setState('loading')
    setError(null)
    setTextContent(null)
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
          setTextContent(text)
          setState('ready')
          return
        }
        const url = URL.createObjectURL(blob)
        if (ownedUrlRef.current !== null) {
          URL.revokeObjectURL(ownedUrlRef.current)
        }
        ownedUrlRef.current = url
        setObjectUrl(url)
        setState('ready')
      })
      .catch((err: unknown) => {
        if (cancelled) {
          return
        }
        setState('failed')
        setError(err instanceof Error ? err.message : 'Failed to load attachment.')
      })

    return () => {
      cancelled = true
    }
  }, [item.id, item.mime, item.previewUrl, loadContent])

  useEffect(() => {
    return () => {
      if (ownedUrlRef.current !== null) {
        URL.revokeObjectURL(ownedUrlRef.current)
        ownedUrlRef.current = null
      }
    }
  }, [])

  const isImage = item.kind === 'image' || item.mime.startsWith('image/')
  const isPdf =
    item.mime === 'application/pdf' || item.filename.toLowerCase().endsWith('.pdf')
  const isText = textContent !== null || isTextLikeMime(item.mime)

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
          {state === 'loading' ? (
            <p
              aria-busy="true"
              className="text-sm text-muted-foreground"
              data-slot="attachment-lightbox-loading"
              role="status"
            >
              Loading attachment…
            </p>
          ) : null}
          {state === 'failed' ? (
            <InlineFeedback role="alert" tone="danger">
              {error ?? 'Failed to load attachment.'}
            </InlineFeedback>
          ) : null}
          {state === 'ready' && isImage && objectUrl !== null ? (
            <img
              alt={item.filename}
              className="mx-auto max-h-[min(80vh,800px)] max-w-full object-contain"
              data-slot="attachment-lightbox-image"
              src={objectUrl}
            />
          ) : null}
          {state === 'ready' && isPdf && objectUrl !== null ? (
            <iframe
              className="h-[min(75vh,720px)] w-full rounded-md border border-border"
              data-slot="attachment-lightbox-pdf"
              src={objectUrl}
              title={item.filename}
            />
          ) : null}
          {state === 'ready' && isText && textContent !== null ? (
            <pre
              className="max-h-[min(75vh,720px)] overflow-auto whitespace-pre-wrap break-words rounded-md border border-border bg-muted/20 p-3 text-xs leading-relaxed text-foreground"
              data-slot="attachment-lightbox-text"
            >
              {textContent}
            </pre>
          ) : null}
          {state === 'ready' &&
          !isImage &&
          !isPdf &&
          textContent === null &&
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
