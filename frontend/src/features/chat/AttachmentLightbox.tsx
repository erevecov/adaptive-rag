import { useEffect, useRef, useState } from 'react'
import { ChevronLeft, ChevronRight, Download, FileText, X } from 'lucide-react'

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

export type AttachmentLightboxGallery = {
  items: AttachmentLightboxItem[]
  index: number
}

type RemoteLoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'ready'; objectUrl: string | null; textContent: string | null }
  | { status: 'failed'; error: string }

export function AttachmentLightbox({
  items,
  initialIndex = 0,
  loadContent,
  onClose,
}: {
  items: AttachmentLightboxItem[]
  initialIndex?: number
  /** Authenticated fetch for remote attachments (transcript history). */
  loadContent?(attachmentId: string): Promise<Blob>
  onClose(): void
}) {
  const safeItems = items
  const [index, setIndex] = useState(() =>
    clampIndex(initialIndex, safeItems.length),
  )
  const item = safeItems[clampIndex(index, safeItems.length)]
  const dialogRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)
  const multi = safeItems.length > 1

  useFocusTrap(dialogRef, true)

  useEffect(() => {
    closeButtonRef.current?.focus()
  }, [])

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented) {
        return
      }
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        return
      }
      if (!multi) {
        return
      }
      if (event.key === 'ArrowLeft') {
        event.preventDefault()
        setIndex((current) =>
          (current - 1 + safeItems.length) % safeItems.length,
        )
        return
      }
      if (event.key === 'ArrowRight') {
        event.preventDefault()
        setIndex((current) => (current + 1) % safeItems.length)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [multi, onClose, safeItems.length])

  if (item === undefined) {
    return null
  }

  const positionLabel = `${clampIndex(index, safeItems.length) + 1} / ${safeItems.length}`

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
            <div className="min-w-0">
              <h2
                className="truncate text-sm font-semibold text-foreground"
                id="attachment-lightbox-title"
                title={item.filename}
              >
                {item.filename}
              </h2>
              {multi ? (
                <p
                  className="text-[11px] tabular-nums text-muted-foreground"
                  data-slot="attachment-lightbox-position"
                >
                  {positionLabel}
                </p>
              ) : null}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
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
        <div className="relative min-h-0 overflow-auto p-3 max-[680px]:p-2">
          {multi ? (
            <>
              <IconButton
                className="absolute left-2 top-1/2 z-10 -translate-y-1/2 bg-background/90 shadow-sm"
                label="Previous attachment"
                onClick={() =>
                  setIndex(
                    (current) =>
                      (current - 1 + safeItems.length) % safeItems.length,
                  )
                }
                type="button"
                variant="secondary"
              >
                <ChevronLeft aria-hidden="true" className="size-5" />
              </IconButton>
              <IconButton
                className="absolute right-2 top-1/2 z-10 -translate-y-1/2 bg-background/90 shadow-sm"
                label="Next attachment"
                onClick={() =>
                  setIndex((current) => (current + 1) % safeItems.length)
                }
                type="button"
                variant="secondary"
              >
                <ChevronRight aria-hidden="true" className="size-5" />
              </IconButton>
            </>
          ) : null}
          {/* Remount body per attachment so load state resets without setState-in-effect. */}
          <AttachmentLightboxBody
            item={item}
            key={item.id}
            loadContent={loadContent}
          />
        </div>
      </div>
    </div>
  )
}

function AttachmentLightboxBody({
  item,
  loadContent,
}: {
  item: AttachmentLightboxItem
  loadContent?(attachmentId: string): Promise<Blob>
}) {
  const ownedUrlRef = useRef<string | null>(null)
  const localPreview = item.previewUrl?.trim() ?? ''
  const hasLocalPreview = localPreview.length > 0

  const [localText, setLocalText] = useState<string | null>(null)
  const [remote, setRemote] = useState<RemoteLoadState>({ status: 'idle' })

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

  useEffect(() => {
    if (hasLocalPreview) {
      return
    }
    if (loadContent === undefined) {
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
    remote.status === 'failed'
      ? remote.error
      : 'Attachment preview is not available.'
  const isReady = hasLocalPreview || remote.status === 'ready'

  const isImage = item.kind === 'image' || item.mime.startsWith('image/')
  const isPdf =
    item.mime === 'application/pdf' ||
    item.filename.toLowerCase().endsWith('.pdf')
  const showText = textContent !== null

  return (
    <>
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
      {isReady && !isImage && !isPdf && !showText && objectUrl !== null ? (
        <div
          className="grid gap-3 p-2 text-sm text-muted-foreground"
          data-slot="attachment-lightbox-binary"
        >
          <p>
            Preview is not available for this file type in the browser. Download
            it to open locally.
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
      {isReady && objectUrl !== null && (isImage || isPdf) ? (
        <div className="mt-2 flex justify-end">
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
        </div>
      ) : null}
    </>
  )
}

function clampIndex(index: number, length: number): number {
  if (length <= 0) {
    return 0
  }
  if (index < 0) {
    return 0
  }
  if (index >= length) {
    return length - 1
  }
  return index
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
