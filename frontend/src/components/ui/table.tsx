import {
  type HTMLAttributes,
  type TableHTMLAttributes,
  type TdHTMLAttributes,
  type ThHTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

/** Numeric columns: right-align + stable digit width while values refresh. */
export const tableNumericClass = 'text-right font-medium tabular-nums'

export type TableScrollProps = HTMLAttributes<HTMLDivElement>

export const TableScroll = forwardRef<HTMLDivElement, TableScrollProps>(
  ({ className, ...props }, ref) => (
    <div
      className={cn(
        // Vertical max-height so sticky TableHeader can pin while scrolling long tables.
        'w-full max-h-[min(70vh,36rem)] overflow-auto overscroll-contain',
        'max-[680px]:max-h-[min(50vh,1.25rem)] max-[680px]:rounded-sm max-[680px]:overscroll-y-contain',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="table-scroll"
    />
  ),
)
TableScroll.displayName = 'TableScroll'

export type TableProps = TableHTMLAttributes<HTMLTableElement>

export const Table = forwardRef<HTMLTableElement, TableProps>(
  ({ className, ...props }, ref) => (
    <table
      className={cn(
        // On narrow viewports shrink min-width so horizontal scroll is less extreme.
        'w-full min-w-[720px] max-[680px]:min-w-[56px] border-collapse text-sm tracking-tight max-[680px]:tracking-tighter',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="table"
    />
  ),
)
Table.displayName = 'Table'

export type TableHeaderProps = HTMLAttributes<HTMLTableSectionElement>

export const TableHeader = forwardRef<
  HTMLTableSectionElement,
  TableHeaderProps
>(({ className, ...props }, ref) => (
  <thead
    className={cn(
      // Opaque card sticky header stays legible on purple/dark nested panels.
      'sticky top-0 z-10 border-b border-border bg-card shadow-[0_1px_0_0] shadow-primary/15 max-[680px]:border-primary/95 max-[680px]:shadow-primary/95',
      className,
    )}
    ref={ref}
    {...props}
    data-slot="table-header"
  />
))
TableHeader.displayName = 'TableHeader'

export type TableBodyProps = HTMLAttributes<HTMLTableSectionElement>

export const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className, ...props }, ref) => (
    <tbody
      className={cn('[&_tr:last-child]:border-0', className)}
      ref={ref}
      {...props}
      data-slot="table-body"
    />
  ),
)
TableBody.displayName = 'TableBody'

export type TableRowProps = HTMLAttributes<HTMLTableRowElement>

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, ...props }, ref) => (
    <tr
      className={cn(
        'border-b border-border motion-safe:transition-colors hover:bg-primary/15 active:bg-primary/20 max-[680px]:active:bg-primary/35 max-[680px]:border-primary/95',
        'focus-visible:bg-primary/15 focus-visible:outline-none',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="table-row"
    />
  ),
)
TableRow.displayName = 'TableRow'

export type TableHeadProps = ThHTMLAttributes<HTMLTableCellElement>

export const TableHead = forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ className, scope = 'col', ...props }, ref) => (
    <th
      className={cn(
        'h-9 max-[680px]:h-11 whitespace-nowrap bg-card px-3 max-[680px]:px-0.5 text-left align-middle text-xs font-semibold uppercase tracking-wide text-muted-foreground motion-safe:transition-colors max-[680px]:text-[0.5625rem] max-[680px]:tracking-tighter',
        className,
      )}
      ref={ref}
      scope={scope}
      {...props}
      data-slot="table-head"
    />
  ),
)
TableHead.displayName = 'TableHead'

export type TableCellProps = TdHTMLAttributes<HTMLTableCellElement>

export const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, ...props }, ref) => (
    <td
      className={cn(
        'whitespace-nowrap px-3 py-2 max-[680px]:min-h-11 max-[680px]:px-0.5 max-[680px]:py-0.5 max-[680px]:text-[0.5625rem] max-[680px]:leading-snug max-[680px]:tracking-tighter align-middle text-foreground tracking-tight',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="table-cell"
    />
  ),
)
TableCell.displayName = 'TableCell'
