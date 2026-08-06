/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  TableScroll,
  tableNumericClass,
} from './table'

afterEach(() => {
  cleanup()
})

describe('tableNumericClass', () => {
  test('exports right-aligned tabular digits for metric columns', () => {
    expect(tableNumericClass).toContain('tabular-nums')
    expect(tableNumericClass).toContain('text-right')
    expect(tableNumericClass).toContain('font-medium')
  })

  test('merges onto TableCell for numeric values', () => {
    render(
      <Table>
        <TableBody>
          <TableRow>
            <TableCell className={tableNumericClass}>1,024</TableCell>
          </TableRow>
        </TableBody>
      </Table>,
    )

    const cell = screen.getByText('1,024')
    expect(cell.className).toContain('tabular-nums')
    expect(cell.className).toContain('text-right')
    expect(cell.className).toContain('font-medium')
  })
})

describe('Table density', () => {
  test('sticky header uses card tint; rows hover for scan', () => {
    render(
      <TableScroll>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Latency</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell>12ms</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableScroll>,
    )

    const scroll = screen.getByText('Latency').closest('[data-slot="table-scroll"]')
    expect(scroll?.className).toContain('overscroll-contain')
    expect(scroll?.className).toContain('max-[680px]:overscroll-y-contain')
    expect(scroll?.className).toContain('max-[680px]:rounded-sm')
    expect(scroll?.className).toContain('max-[680px]:max-h-[min(50vh,4rem)]')
    const header = screen.getByText('Latency').closest('[data-slot="table-header"]')
    expect(header?.className).toContain('bg-card')
    expect(header?.className).toContain('shadow-primary/15')
    expect(header?.className).not.toContain('bg-card/95')
    expect(header?.className).not.toContain('backdrop-blur')
    expect(screen.getByText('Latency').className).toContain('tracking-wide')
    expect(screen.getByText('Latency').className).toContain('motion-safe:transition-colors')
    expect(screen.getByText('Latency').className).toContain('h-9')
    expect(screen.getByText('Latency').className).toContain('max-[680px]:h-11')
    expect(screen.getByText('Latency').className).toContain('max-[680px]:text-[0.5625rem]')
    expect(screen.getByText('12ms').className).toContain('max-[680px]:min-h-11')
    expect(screen.getByText('12ms').className).toContain('max-[680px]:py-0.5')
    expect(screen.getByText('12ms').className).toContain('max-[680px]:text-[0.5625rem]')
    expect(screen.getByText('12ms').className).toContain('max-[680px]:leading-snug')
    expect(screen.getByText('12ms').className).toContain('max-[680px]:tracking-tighter')
    expect(screen.getByText('12ms').closest('[data-slot="table"]')?.className).toContain(
      'max-[680px]:min-w-[160px]',
    )
    expect(screen.getByText('12ms').closest('[data-slot="table"]')?.className).toContain(
      'max-[680px]:tracking-tighter',
    )
    expect(screen.getByText('12ms').closest('[data-slot="table-row"]')?.className).toContain(
      'hover:bg-primary/15',
    )
    expect(screen.getByText('12ms').closest('[data-slot="table-row"]')?.className).toContain(
      'active:bg-primary/20',
    )
    expect(screen.getByText('12ms').closest('[data-slot="table-row"]')?.className).toContain(
      'focus-visible:bg-primary/15',
    )
    expect(screen.getByText('12ms').closest('[data-slot="table-row"]')?.className).toContain(
      'max-[680px]:border-primary/95',
    )
  })
})
