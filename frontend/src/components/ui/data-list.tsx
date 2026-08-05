import { type HTMLAttributes, forwardRef } from 'react'

import { cn } from '@/lib/utils'

export type DataListProps = HTMLAttributes<HTMLUListElement>

export const DataList = forwardRef<HTMLUListElement, DataListProps>(
  ({ className, ...props }, ref) => (
    <ul
      className={cn('grid gap-2 max-[680px]:gap-1', className)}
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
        'min-w-0 rounded-md border border-border bg-card p-3 text-sm tracking-tight text-card-foreground max-[680px]:p-1.5 max-[680px]:leading-snug',
        'motion-safe:transition-colors hover:bg-primary/15',
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
      'flex flex-wrap items-center gap-2 max-[680px]:gap-1',
      className,
    )}
    ref={ref}
    {...props}
    data-slot="data-list-item-actions"
  />
))
DataListItemActions.displayName = 'DataListItemActions'
