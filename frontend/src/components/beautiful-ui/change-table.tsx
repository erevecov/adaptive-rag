import { type ReactNode } from 'react'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
} from '@/components/ui/table'

export type ChangeTableRow = {
  field: string
  id: string
  original: ReactNode
  proposed: ReactNode
}

export type ChangeTableProps = { label: string; rows: readonly ChangeTableRow[] }

export function ChangeTable({ label, rows }: ChangeTableProps) {
  return (
    <section
      aria-label={label}
      className="grid gap-2 rounded-[2px] border border-border bg-card p-3 motion-safe:transition-colors max-[680px]:gap-1 max-[680px]:p-2"
      data-slot="change-table"
    >
      <h2 className="text-sm font-medium">{label}</h2>
      <TableScroll className="border border-border">
        <Table aria-label={label}>
          <caption className="sr-only">{label}</caption>
          <TableHeader>
            <TableRow>
              <TableHead>Field</TableHead>
              <TableHead>Original</TableHead>
              <TableHead>Proposed</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={row.id}>
                <TableHead scope="row">{row.field}</TableHead>
                <TableCell>{row.original}</TableCell>
                <TableCell>{row.proposed}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableScroll>
    </section>
  )
}
