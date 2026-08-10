import {
  type ChangeEvent,
  type RefObject,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import { FileText, X } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type ChatAttachmentUploadResponse = {
  id: string
  kind: 'image' | 'document'
  filename: string
  mime: string
  size_bytes: number
}

export type LocalAttachment = {
  localId: string
  file: File
  previewUrl: string
  status: 'uploading' | 'ready' | 'failed'
  attachmentId?: string
  kind?: 'image' | 'document'
  error?: string
}

export const MAX_CHAT_ATTACHMENTS = 5

const ACCEPT_ATTR = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/gif',
  'text/plain',
  'text/markdown',
  '.md',
  '.markdown',
  '.txt',
  'application/pdf',
  '.pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  '.docx',
].join(',')

export function AttachmentChips({
  attachments,
  onRemove,
  readOnly = false,
}: {
  attachments: Array<{
    localId: string
    filename: string
    previewUrl?: string
    kind?: 'image' | 'document'
    status?: LocalAttachment['status']
    error?: string
  }>
  onRemove?(localId: string): void
  readOnly?: boolean
}) {
  if (attachments.length === 0) {
    return null
  }
  return (
    <ul
      aria-label="Attachments"
      className="flex flex-wrap gap-1.5"
      data-slot="chat-attachment-chips"
    >
      {attachments.map((item) => {
        const isImage = item.kind === 'image' && item.previewUrl
        return (
          <li
            className={cn(
              'flex max-w-[12rem] items-center gap-1.5 rounded-md border border-border/80 bg-background px-1.5 py-1 text-[11px] tracking-tight',
              item.status === 'uploading' && 'opacity-60',
              item.status === 'failed' && 'border-destructive',
            )}
            key={item.localId}
            title={item.error}
          >
            {isImage ? (
              <img
                alt=""
                className="size-6 shrink-0 rounded object-cover"
                height={24}
                src={item.previewUrl}
                width={24}
              />
            ) : (
              <FileText aria-hidden="true" className="size-3.5 shrink-0 text-muted-foreground" />
            )}
            <span className="min-w-0 truncate text-foreground">
              {item.filename}
            </span>
            {!readOnly && onRemove !== undefined ? (
              <Button
                aria-label={`Remove attachment ${item.filename}`}
                className="size-6 shrink-0 p-0 text-muted-foreground hover:text-foreground"
                onClick={() => onRemove(item.localId)}
                size="icon"
                type="button"
                variant="ghost"
              >
                <X aria-hidden="true" className="size-3.5" />
              </Button>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}

export function useChatAttachments({
  upload,
  deleteRemote,
  maxAttachments = MAX_CHAT_ATTACHMENTS,
}: {
  upload(file: File): Promise<ChatAttachmentUploadResponse>
  deleteRemote?(attachmentId: string): Promise<void>
  maxAttachments?: number
}) {
  const [attachments, setAttachments] = useState<LocalAttachment[]>([])
  const attachmentsRef = useRef(attachments)
  attachmentsRef.current = attachments

  const revokePreview = useCallback((url: string) => {
    if (url.startsWith('blob:')) {
      URL.revokeObjectURL(url)
    }
  }, [])

  const reset = useCallback(() => {
    setAttachments((current) => {
      for (const item of current) {
        revokePreview(item.previewUrl)
      }
      return []
    })
  }, [revokePreview])

  useEffect(() => {
    return () => {
      for (const item of attachmentsRef.current) {
        revokePreview(item.previewUrl)
      }
    }
  }, [revokePreview])

  const remove = useCallback(
    (localId: string) => {
      setAttachments((current) => {
        const target = current.find((item) => item.localId === localId)
        if (target === undefined) {
          return current
        }
        revokePreview(target.previewUrl)
        if (
          target.attachmentId !== undefined &&
          deleteRemote !== undefined
        ) {
          void deleteRemote(target.attachmentId).catch(() => {
            // Best-effort remote delete; chip is already gone.
          })
        }
        return current.filter((item) => item.localId !== localId)
      })
    },
    [deleteRemote, revokePreview],
  )

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const list = Array.from(files)
      if (list.length === 0) {
        return
      }
      setAttachments((current) => {
        const room = Math.max(0, maxAttachments - current.length)
        if (room === 0) {
          return current
        }
        const admitted = list.slice(0, room)
        const next = [...current]
        for (const file of admitted) {
          const localId = `local-${crypto.randomUUID()}`
          const previewUrl = URL.createObjectURL(file)
          next.push({
            localId,
            file,
            previewUrl,
            status: 'uploading',
          })
          void upload(file)
            .then((response) => {
              setAttachments((latest) =>
                latest.map((item) =>
                  item.localId === localId
                    ? {
                        ...item,
                        status: 'ready',
                        attachmentId: response.id,
                        kind: response.kind,
                      }
                    : item,
                ),
              )
            })
            .catch((error: unknown) => {
              const message =
                error instanceof Error ? error.message : 'Upload failed'
              setAttachments((latest) =>
                latest.map((item) =>
                  item.localId === localId
                    ? { ...item, status: 'failed', error: message }
                    : item,
                ),
              )
            })
        }
        return next
      })
    },
    [maxAttachments, upload],
  )

  const readyAttachments = useMemo(
    () =>
      attachments.filter(
        (item): item is LocalAttachment & { attachmentId: string } =>
          item.status === 'ready' && item.attachmentId !== undefined,
      ),
    [attachments],
  )

  const blocked = attachments.some(
    (item) => item.status === 'uploading' || item.status === 'failed',
  )

  const atCap = attachments.length >= maxAttachments

  return {
    attachments,
    readyAttachments,
    blocked,
    atCap,
    accept: ACCEPT_ATTR,
    addFiles,
    remove,
    reset,
  }
}

export function AttachmentFileInput({
  accept,
  disabled,
  inputRef,
  onChange,
}: {
  accept: string
  disabled?: boolean
  inputRef: RefObject<HTMLInputElement | null>
  onChange(event: ChangeEvent<HTMLInputElement>): void
}) {
  return (
    <input
      accept={accept}
      className="sr-only"
      disabled={disabled}
      multiple
      onChange={onChange}
      ref={inputRef}
      type="file"
    />
  )
}
