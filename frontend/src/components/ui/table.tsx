import {
  type HTMLAttributes,
  type TableHTMLAttributes,
  type TdHTMLAttributes,
  type ThHTMLAttributes,
  forwardRef,
} from 'react'

import { cn } from '@/lib/utils'

export type TableScrollProps = HTMLAttributes<HTMLDivElement>

export const TableScroll = forwardRef<HTMLDivElement, TableScrollProps>(
  ({ className, ...props }, ref) => (
    <div
      className={cn('w-full overflow-x-auto', className)}
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
      className={cn('w-full min-w-[720px] border-collapse text-sm', className)}
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
  <thead className={cn('border-b border-border', className)} ref={ref} {...props} data-slot="table-header" />
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
      className={cn('border-b border-border transition-colors', className)}
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
        'h-10 whitespace-nowrap px-3 text-left align-middle text-xs font-semibold uppercase tracking-normal text-muted-foreground',
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
        'whitespace-nowrap px-3 py-2 align-middle text-foreground',
        className,
      )}
      ref={ref}
      {...props}
      data-slot="table-cell"
    />
  ),
)
TableCell.displayName = 'TableCell'
