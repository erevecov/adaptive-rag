import { Copy } from 'lucide-react'

import { IconButton } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export type CodeStreamProps = {
  code: string
  copyLabel: string
  filename?: string
  language?: string
  onCopy?(code: string): void | Promise<void>
}

export function CodeStream({
  code,
  copyLabel,
  filename,
  language,
  onCopy,
}: CodeStreamProps) {
  const label = filename ? `Code: ${filename}` : 'Code'
  const lines = code.split('\n')

  return (
    <section className="overflow-hidden rounded-[2px] border border-border bg-muted/20" data-slot="code-stream">
      <header className="flex min-h-9 items-center gap-2 border-b border-border px-3 py-1.5 text-xs text-muted-foreground max-[680px]:min-h-11">
        {filename ? <span className="min-w-0 flex-1 truncate font-medium text-foreground">{filename}</span> : <span className="flex-1" />}
        {language ? <span className="tabular-nums">{language}</span> : null}
        <IconButton disabled={!onCopy} label={copyLabel} onClick={() => onCopy?.(code)} variant="ghost">
          <Copy aria-hidden="true" className="size-4" />
        </IconButton>
      </header>
      <pre
        aria-label={label}
        className={cn('overflow-x-auto p-3 text-sm leading-relaxed text-foreground', 'max-[680px]:text-xs')}
      >
        <code className={language ? `language-${language}` : undefined}>
          {lines.map((line, index) => (
            <span className="grid grid-cols-[2ch_minmax(0,1fr)] gap-3" key={`${index}-${line}`}>
              <span
                aria-hidden="true"
                className="select-none text-right tabular-nums text-muted-foreground"
                data-slot="code-stream-line-number"
              >
                {index + 1}
              </span>
              <span>{line}</span>
              {index < lines.length - 1 ? '\n' : null}
            </span>
          ))}
        </code>
      </pre>
    </section>
  )
}
