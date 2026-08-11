import { useId, useMemo, useState } from 'react'

import { Input } from '@/components/ui/control'
import { EmptyState } from '@/components/ui/feedback'

export type CommandSearchItem = { id: string; label: string; meta?: string }

export type CommandSearchProps = {
  emptyLabel: string
  items: readonly CommandSearchItem[]
  label: string
  onSelect(id: string): void
  placeholder: string
}

export function CommandSearch({
  emptyLabel,
  items,
  label,
  onSelect,
  placeholder,
}: CommandSearchProps) {
  const inputId = useId()
  const [query, setQuery] = useState('')
  const matches = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase()
    return normalizedQuery.length === 0
      ? items
      : items.filter((item) => item.label.toLocaleLowerCase().includes(normalizedQuery))
  }, [items, query])

  return (
    <section aria-label={label} className="grid gap-2" data-slot="command-search">
      <label className="sr-only" htmlFor={inputId}>
        {label}
      </label>
      <Input
        id={inputId}
        onChange={(event) => setQuery(event.target.value)}
        placeholder={placeholder}
        type="search"
        value={query}
      />
      {matches.length === 0 ? (
        <EmptyState>{emptyLabel}</EmptyState>
      ) : (
        <ul className="overflow-hidden rounded-[2px] border border-border">
          {matches.map((item) => (
            <li className="border-b border-border last:border-b-0" key={item.id}>
              <button
                className="flex min-h-9 w-full items-center gap-2 px-3 text-left text-sm motion-safe:transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-[680px]:min-h-11"
                onClick={() => onSelect(item.id)}
                type="button"
              >
                <span className="min-w-0 flex-1 truncate">{item.label}</span>
                {item.meta ? <span className="text-xs text-muted-foreground">{item.meta}</span> : null}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
