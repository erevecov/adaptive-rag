import { isValidElement, type ReactNode, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { CodeStream } from '@/components/beautiful-ui'
import type { RetrievalResult } from '@/lib/apiClient'
import { cn } from '@/lib/utils'

type MarkdownAnswerProps = {
  children: string
  className?: string
  /** Citations for the turn — used to map [doc-N], [N], and [chunk-uuid] markers. */
  citations?: readonly RetrievalResult[]
  /** Map 1-based citation ordinals to open handlers. */
  onCitationClick?: (ordinal: number) => void
}

/**
 * Renders chat answers as GitHub-flavored markdown.
 * Citation markers become beflow-style `doc-N` chips when a click handler exists:
 * - `[doc-1]` / `[1]`
 * - `[uuid]` matching a cited chunk_id / citation.chunk_id / source_id
 */
export function MarkdownAnswer({
  children,
  className,
  citations = [],
  onCitationClick,
}: MarkdownAnswerProps) {
  const idToOrdinal = useMemo(
    () => buildCitationIdIndex(citations),
    [citations],
  )

  const components = useMemo(
    () => ({
      p: ({ children: node }: { children?: ReactNode }) => (
        <p className="mb-2 last:mb-0 whitespace-pre-wrap leading-relaxed">
          {renderInlineWithCitations(node, onCitationClick, idToOrdinal)}
        </p>
      ),
      li: ({ children: node }: { children?: ReactNode }) => (
        <li className="leading-relaxed">
          {renderInlineWithCitations(node, onCitationClick, idToOrdinal)}
        </li>
      ),
      strong: ({ children: node }: { children?: ReactNode }) => (
        <strong className="font-semibold text-foreground">{node}</strong>
      ),
      em: ({ children: node }: { children?: ReactNode }) => (
        <em className="italic">{node}</em>
      ),
      a: ({
        href,
        children: node,
      }: {
        href?: string
        children?: ReactNode
      }) => (
        <a
          className="font-medium text-primary underline-offset-2 hover:underline"
          href={href}
          rel="noreferrer"
          target="_blank"
        >
          {node}
        </a>
      ),
      ul: ({ children: node }: { children?: ReactNode }) => (
        <ul className="mb-2 list-disc space-y-1 pl-5 last:mb-0">{node}</ul>
      ),
      ol: ({ children: node }: { children?: ReactNode }) => (
        <ol className="mb-2 list-decimal space-y-1 pl-5 last:mb-0">{node}</ol>
      ),
      h1: ({ children: node }: { children?: ReactNode }) => (
        <h3 className="mb-2 text-base font-semibold tracking-tight">{node}</h3>
      ),
      h2: ({ children: node }: { children?: ReactNode }) => (
        <h3 className="mb-2 text-sm font-semibold tracking-tight">{node}</h3>
      ),
      h3: ({ children: node }: { children?: ReactNode }) => (
        <h4 className="mb-1.5 text-sm font-semibold tracking-tight">{node}</h4>
      ),
      code: ({
        className: codeClass,
        children: node,
      }: {
        className?: string
        children?: ReactNode
      }) => (
        <code
          className={cn(
            'rounded bg-muted/50 px-1 py-0.5 font-mono text-[0.85em]',
            codeClass,
          )}
        >
          {node}
        </code>
      ),
      pre: ({ children: node }: { children?: ReactNode }) => {
        if (!isValidElement<{ children?: ReactNode; className?: string }>(node)) {
          return <pre>{node}</pre>
        }
        const code = String(node.props.children ?? '').replace(/\n$/, '')
        const language = node.props.className?.match(
          /(?:^|\s)language-([^\s]+)/,
        )?.[1]
        return (
          <div className="mb-2 last:mb-0" data-slot="markdown-code-block">
            <MarkdownCodeBlock code={code} language={language} />
          </div>
        )
      },
      blockquote: ({ children: node }: { children?: ReactNode }) => (
        <blockquote className="mb-2 border-l-2 border-primary/40 pl-3 text-muted-foreground last:mb-0">
          {node}
        </blockquote>
      ),
    }),
    [idToOrdinal, onCitationClick],
  )

  return (
    <div
      className={cn(
        'text-sm tracking-tight text-card-foreground max-[680px]:text-sm',
        className,
      )}
      data-slot="markdown-answer"
    >
      <ReactMarkdown components={components} remarkPlugins={[remarkGfm]}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

function MarkdownCodeBlock({
  code,
  language,
}: {
  code: string
  language?: string
}) {
  const [copyResult, setCopyResult] = useState<'error' | 'success' | null>(null)
  const clipboard =
    typeof navigator !== 'undefined' &&
    typeof navigator.clipboard?.writeText === 'function'
      ? navigator.clipboard
      : null

  async function copyCode(codeToCopy: string) {
    if (clipboard === null) {
      return
    }

    setCopyResult(null)
    try {
      await clipboard.writeText(codeToCopy)
      setCopyResult('success')
    } catch {
      setCopyResult('error')
    }
  }

  return (
    <>
      <CodeStream
        code={code}
        copyLabel="Copy code"
        language={language}
        onCopy={clipboard === null ? undefined : copyCode}
      />
      {copyResult !== null ? (
        <span aria-live="polite" className="sr-only" role="status">
          {copyResult === 'success'
            ? 'Code copied to clipboard.'
            : 'Code could not be copied.'}
        </span>
      ) : null}
    </>
  )
}

/** `[doc-1]`, `[1]`, or `[uuid]` (chunk/source id). */
const CITATION_MARK =
  /\[(?:doc-)?(\d+)\]|\[([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\]/gi

function buildCitationIdIndex(
  citations: readonly RetrievalResult[],
): Map<string, number> {
  const map = new Map<string, number>()
  citations.forEach((citation, index) => {
    const ordinal = index + 1
    const ids = [
      citation.chunk_id,
      citation.citation.chunk_id,
      citation.citation.source_id,
      citation.citation.document_id,
    ]
    for (const id of ids) {
      if (typeof id === 'string' && id.trim().length > 0) {
        map.set(id.trim().toLowerCase(), ordinal)
      }
    }
  })
  return map
}

function resolveOrdinal(
  match: RegExpExecArray,
  idToOrdinal: Map<string, number>,
): number | null {
  const numeric = match[1]
  if (numeric !== undefined) {
    const n = Number(numeric)
    return Number.isFinite(n) && n >= 1 ? n : null
  }
  const uuid = match[2]
  if (uuid === undefined) {
    return null
  }
  return idToOrdinal.get(uuid.toLowerCase()) ?? null
}

function CitationChip({
  ordinal,
  onCitationClick,
}: {
  ordinal: number
  onCitationClick?: (ordinal: number) => void
}) {
  const label = `doc-${ordinal}`
  if (onCitationClick === undefined) {
    return (
      <span
        className={cn(
          'mx-0.5 inline-flex items-center rounded-sm border border-border px-1.5 py-px',
          'align-baseline text-[10px] font-medium leading-none tabular-nums',
          'text-muted-foreground',
        )}
        data-slot="citation-chip"
      >
        {label}
      </span>
    )
  }
  return (
    <button
      aria-label={label}
      className={cn(
        'mx-0.5 inline-flex items-center rounded-sm border border-border px-1.5 py-px',
        'align-baseline text-[10px] font-medium leading-none tabular-nums',
        'text-muted-foreground transition-colors',
        'hover:border-foreground/40 hover:text-foreground',
      )}
      data-slot="citation-chip"
      onClick={() => onCitationClick(ordinal)}
      type="button"
    >
      {label}
    </button>
  )
}

function renderInlineWithCitations(
  node: ReactNode,
  onCitationClick: ((ordinal: number) => void) | undefined,
  idToOrdinal: Map<string, number>,
): ReactNode {
  if (typeof node !== 'string') {
    if (Array.isArray(node)) {
      return node.map((child, index) => (
        <span key={index}>
          {renderInlineWithCitations(child, onCitationClick, idToOrdinal)}
        </span>
      ))
    }
    return node
  }
  const parts: ReactNode[] = []
  let last = 0
  let match: RegExpExecArray | null
  const re = new RegExp(CITATION_MARK.source, 'gi')
  while ((match = re.exec(node)) !== null) {
    if (match.index > last) {
      parts.push(node.slice(last, match.index))
    }
    const ordinal = resolveOrdinal(match, idToOrdinal)
    if (ordinal === null) {
      // Unknown UUID / out-of-range — drop raw bracket junk (do not show UUID).
      // Keep numeric markers that are out of range as literal text.
      if (match[1] !== undefined) {
        parts.push(match[0])
      }
    } else {
      parts.push(
        <CitationChip
          key={`${match.index}-${ordinal}`}
          onCitationClick={onCitationClick}
          ordinal={ordinal}
        />,
      )
    }
    last = match.index + match[0].length
  }
  if (last < node.length) {
    parts.push(node.slice(last))
  }
  return parts.length > 0 ? parts : node
}
