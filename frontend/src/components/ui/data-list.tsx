import { type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export type DataListProps = HTMLAttributes<HTMLUListElement>

export const DataList = forwardRef<HTMLUListElement, DataListProps>(
  ({ className, ...props }, ref) => (
    <ul
      className={cn('grid gap-2 max-[680px]:gap-0.5', className)}
      ref={ref}
      {...props}
      data-slot="data-list"
    />
  ),
)
DataList.displayName = 'DataList'

export type DataListItemProps = HTMLAttributes<HTMLLIElement>

export const DataListItem = forwardRef<HTMLLIElement, DataListItemProps>(
  ({ className, ...props }, ref) => (
    <li
      className={cn(
        'min-w-0 rounded-md border border-border bg-card p-3 text-sm tracking-tight text-card-foreground max-[680px]:rounded-sm max-[680px]:border-primary/95 max-[680px]:p-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter max-[680px]:shadow-[0_1px_0_0] max-[680px]:shadow-primary/95',
        'motion-safe:transition-colors hover:bg-primary/15 active:bg-primary/20 max-[680px]:active:bg-primary/45',
        'focus-visible:outline-none focus-visible:bg-primary/15 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="data-list-item"
    />
  ),
)
DataListItem.displayName = 'DataListItem'

export type DataListItemActionsProps = HTMLAttributes<HTMLDivElement>

export const DataListItemActions = forwardRef<
  HTMLDivElement,
  DataListItemActionsProps
>(({ className, ...props }, ref) => (
  <div
    className={cn(
      'flex flex-wrap items-center gap-2 max-[680px]:gap-0.5',
      className,
    )}
    ref={ref}
    {...props}
    data-slot="data-list-item-actions"
  />
))
DataListItemActions.displayName = 'DataListItemActions'
