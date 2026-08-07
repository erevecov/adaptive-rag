import { type ReactNode, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

import { cn } from '@/lib/utils'

type MarkdownAnswerProps = {
  children: string
  className?: string
  /** Map [doc-N] / [N] markers to citation open handlers (1-based). */
  onCitationClick?: (ordinal: number) => void
}

/**
 * Renders chat answers as GitHub-flavored markdown.
 * Citation markers like [doc-1] or [1] become clickable chips when handlers exist.
 */
export function MarkdownAnswer({
  children,
  className,
  onCitationClick,
}: MarkdownAnswerProps) {
  const components = useMemo(
    () => ({
      p: ({ children: node }: { children?: ReactNode }) => (
        <p className="mb-2 last:mb-0 whitespace-pre-wrap leading-relaxed">
          {renderInlineWithCitations(node, onCitationClick)}
        </p>
      ),
      li: ({ children: node }: { children?: ReactNode }) => (
        <li className="leading-relaxed">
          {renderInlineWithCitations(node, onCitationClick)}
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
      }) => {
        const isBlock = Boolean(codeClass) || String(node).includes('\n')
        if (isBlock) {
          return (
            <code
              className={cn(
                'block overflow-x-auto rounded-md border border-border bg-muted/40 p-2.5 font-mono text-[12px] leading-relaxed',
                codeClass,
              )}
            >
              {node}
            </code>
          )
        }
        return (
          <code className="rounded bg-muted/50 px-1 py-0.5 font-mono text-[0.85em]">
            {node}
          </code>
        )
      },
      pre: ({ children: node }: { children?: ReactNode }) => (
        <pre className="mb-2 overflow-x-auto last:mb-0">{node}</pre>
      ),
      blockquote: ({ children: node }: { children?: ReactNode }) => (
        <blockquote className="mb-2 border-l-2 border-primary/40 pl-3 text-muted-foreground last:mb-0">
          {node}
        </blockquote>
      ),
    }),
    [onCitationClick],
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

const CITATION_MARK = /\[(?:doc-)?(\d+)\]/gi

function renderInlineWithCitations(
  node: ReactNode,
  onCitationClick?: (ordinal: number) => void,
): ReactNode {
  if (typeof node !== 'string' || onCitationClick === undefined) {
    if (Array.isArray(node)) {
      return node.map((child, index) => (
        <span key={index}>{renderInlineWithCitations(child, onCitationClick)}</span>
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
    const ordinal = Number(match[1])
    parts.push(
      <button
        className="mx-0.5 inline-flex size-5 items-center justify-center rounded-full bg-primary/15 text-[10px] font-semibold tabular-nums text-foreground hover:bg-primary/25"
        key={`${match.index}-${ordinal}`}
        onClick={() => onCitationClick(ordinal)}
        type="button"
      >
        {ordinal}
      </button>,
    )
    last = match.index + match[0].length
  }
  if (last < node.length) {
    parts.push(node.slice(last))
  }
  return parts.length > 0 ? parts : node
}
