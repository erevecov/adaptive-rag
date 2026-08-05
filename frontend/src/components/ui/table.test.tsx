/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, test } from 'vitest'

import { Table, TableBody, TableCell, TableRow, tableNumericClass } from './table'

afterEach(() => {
  cleanup()
})

describe('tableNumericClass', () => {
  test('exports right-aligned tabular digits for metric columns', () => {
    expect(tableNumericClass).toContain('tabular-nums')
    expect(tableNumericClass).toContain('text-right')
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
  })
})
