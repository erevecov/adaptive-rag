import { type ReactNode, useMemo, useState } from 'react'

import { EmptyState } from '@/components/ui/feedback'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'

export type RecordsGridColumn<Row> = {
  header: string
  id: string
  render(row: Row): ReactNode
  sortValue?(row: Row): string | number
}

export type RecordsGridProps<Row extends { id: string }> = {
  columns: readonly RecordsGridColumn<Row>[]
  emptyLabel: string
  label: string
  rows: readonly Row[]
}

type SortState = { columnId: string; direction: 'ascending' | 'descending' }

export function RecordsGrid<Row extends { id: string }>({
  columns,
  emptyLabel,
  label,
  rows,
}: RecordsGridProps<Row>) {
  const [sort, setSort] = useState<SortState | null>(null)
  const sortedRows = useMemo(() => {
    if (!sort) return rows

    const column = columns.find((candidate) => candidate.id === sort.columnId)
    if (!column?.sortValue) return rows

    return [...rows].sort((left, right) => {
      const leftValue = column.sortValue!(left)
      const rightValue = column.sortValue!(right)
      const comparison =
        typeof leftValue === 'number' && typeof rightValue === 'number'
          ? leftValue - rightValue
          : String(leftValue).localeCompare(String(rightValue))
      return sort.direction === 'ascending' ? comparison : -comparison
    })
  }, [columns, rows, sort])

  function toggleSort(column: RecordsGridColumn<Row>) {
    if (!column.sortValue) return
    setSort((current) => ({
      columnId: column.id,
      direction:
        current?.columnId === column.id && current.direction === 'ascending'
          ? 'descending'
          : 'ascending',
    }))
  }

  return (
    <section aria-label={label} className="grid gap-2" data-slot="records-grid">
      <h2 className="text-sm font-medium">{label}</h2>
      {rows.length === 0 ? (
        <EmptyState>{emptyLabel}</EmptyState>
      ) : (
        <TableScroll className="border border-border">
          <Table aria-label={label}>
            <caption className="sr-only">{label}</caption>
            <TableHeader>
              <TableRow>
                {columns.map((column) => {
                  const isSorted = sort?.columnId === column.id
                  return (
                    <TableHead key={column.id} aria-sort={isSorted ? sort.direction : 'none'}>
                      {column.sortValue ? (
                        <button
                          className="min-h-9 text-left font-inherit uppercase focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-[680px]:min-h-11"
                          onClick={() => toggleSort(column)}
                          type="button"
                        >
                          {column.header}
                        </button>
                      ) : (
                        column.header
                      )}
                    </TableHead>
                  )
                })}
              </TableRow>
            </TableHeader>
            <TableBody>
              {sortedRows.map((row) => (
                <TableRow key={row.id}>
                  {columns.map((column) => (
                    <TableCell className={cn('max-[680px]:min-h-11')} key={column.id}>
                      {column.render(row)}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableScroll>
      )}
    </section>
  )
}
