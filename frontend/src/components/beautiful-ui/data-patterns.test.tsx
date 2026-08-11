/**
 * @vitest-environment jsdom
 */
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, test, vi } from 'vitest'

import { CommandSearch } from './command-search'
import { FilteredTaskTable } from './filtered-task-table'
import { InsightDeck } from './insight-deck'
import { ParameterTuner } from './parameter-tuner'
import { RecordsGrid } from './records-grid'
import { WorkspaceNavigation } from './workspace-navigation'

afterEach(() => {
  cleanup()
})

const columns = [
  {
    header: 'Name',
    id: 'name',
    render: (row: { id: string; name: string }) => row.name,
    sortValue: (row: { id: string; name: string }) => row.name,
  },
] as const

describe('RecordsGrid', () => {
  test('sorts a sortable column without mutating caller rows', async () => {
    const user = userEvent.setup()
    const rows = [
      { id: 'b', name: 'Beta' },
      { id: 'a', name: 'Alpha' },
    ] as const
    render(<RecordsGrid columns={columns} emptyLabel="No records" label="Records" rows={rows} />)

    await user.click(screen.getByRole('button', { name: /Name/ }))

    expect(screen.getAllByRole('row')[1].textContent).toContain('Alpha')
    expect(rows[0].name).toBe('Beta')
    expect(screen.getByRole('table', { name: 'Records' }).querySelector('caption')?.textContent).toBe(
      'Records',
    )
  })

  test('renders its supplied empty label when there are no rows', () => {
    render(<RecordsGrid columns={columns} emptyLabel="No records" label="Records" rows={[]} />)

    expect(screen.getByText('No records')).toBeTruthy()
  })

  test('reports descending sort and retains the caller order for equal sort values', async () => {
    const user = userEvent.setup()
    const rows = [
      { id: 'beta-first', name: 'Beta', ordinal: 'first' },
      { id: 'beta-second', name: 'Beta', ordinal: 'second' },
      { id: 'alpha', name: 'Alpha', ordinal: 'only' },
    ]
    render(
      <RecordsGrid
        columns={[
          {
            header: 'Name',
            id: 'name',
            render: (row) => `${row.name} ${row.ordinal}`,
            sortValue: (row) => row.name,
          },
        ]}
        emptyLabel="No records"
        label="Records"
        rows={rows}
      />,
    )

    const sortButton = screen.getByRole('button', { name: 'Name' })
    await user.click(sortButton)
    await user.click(sortButton)

    expect(screen.getByRole('columnheader', { name: 'Name' }).getAttribute('aria-sort')).toBe(
      'descending',
    )
    expect(screen.getAllByRole('row').slice(1).map((row) => row.textContent)).toEqual([
      'Beta first',
      'Beta second',
      'Alpha only',
    ])
  })
})

describe('FilteredTaskTable', () => {
  test('emits the exact selected filter id', async () => {
    const user = userEvent.setup()
    const onFilterChange = vi.fn()
    render(
      <FilteredTaskTable
        activeFilter="all"
        columns={columns}
        emptyLabel="No tasks"
        filters={[
          { id: 'all', label: 'All' },
          { id: 'running', label: 'Running' },
        ]}
        label="Tasks"
        onFilterChange={onFilterChange}
        rows={[]}
      />,
    )

    expect(screen.getByRole('button', { name: 'All' }).getAttribute('aria-pressed')).toBe('true')
    expect(screen.getByRole('button', { name: 'Running' }).getAttribute('aria-pressed')).toBe('false')
    await user.click(screen.getByRole('button', { name: 'Running' }))

    expect(onFilterChange).toHaveBeenCalledWith('running')
    expect(onFilterChange).toHaveBeenCalledTimes(1)
  })

  test('owns one named region while embedding its records grid', () => {
    const { container } = render(
      <FilteredTaskTable
        activeFilter="all"
        columns={columns}
        emptyLabel="No tasks"
        filters={[{ id: 'all', label: 'All' }]}
        label="Task history"
        onFilterChange={() => undefined}
        rows={[{ id: 'task-1', name: 'Index handbook' }]}
      />,
    )

    expect(screen.getAllByRole('region', { name: 'Task history' })).toHaveLength(1)
    expect(container.querySelector('[data-slot="records-grid"]')?.tagName).toBe('DIV')
  })
})

describe('WorkspaceNavigation', () => {
  test('marks the active item and emits its exact navigation id', async () => {
    const user = userEvent.setup()
    const onNavigate = vi.fn()
    render(
      <WorkspaceNavigation
        label="Workspace"
        onNavigate={onNavigate}
        sections={[
          {
            id: 'main',
            items: [
              { active: true, id: 'overview', label: 'Overview' },
              { id: 'sources', label: 'Sources', badge: 3 },
            ],
            label: 'Main',
          },
        ]}
      />,
    )

    expect(screen.getByRole('button', { name: 'Overview' }).getAttribute('aria-current')).toBe('page')
    await user.click(screen.getByRole('button', { name: /Sources/ }))

    expect(onNavigate).toHaveBeenCalledWith('sources')
  })
})

describe('CommandSearch', () => {
  test('filters case-insensitively and emits the selected id', async () => {
    const user = userEvent.setup()
    const onSelect = vi.fn()
    render(
      <CommandSearch
        emptyLabel="No matches"
        items={[{ id: 's-1', label: 'Architecture Guide' }]}
        label="Search sources"
        onSelect={onSelect}
        placeholder="Search"
      />,
    )

    await user.type(screen.getByRole('searchbox'), 'architecture')
    await user.click(screen.getByRole('button', { name: /Architecture Guide/ }))

    expect(onSelect).toHaveBeenCalledWith('s-1')
  })

  test('renders the supplied empty label when nothing matches', async () => {
    const user = userEvent.setup()
    render(
      <CommandSearch
        emptyLabel="No matches"
        items={[{ id: 's-1', label: 'Architecture Guide' }]}
        label="Search sources"
        onSelect={() => undefined}
        placeholder="Search"
      />,
    )

    await user.type(screen.getByRole('searchbox'), 'missing')

    expect(screen.getByText('No matches')).toBeTruthy()
  })

  test('assigns distinct search input ids to multiple instances', () => {
    render(
      <>
        <CommandSearch
          emptyLabel="No matches"
          items={[]}
          label="Search sources"
          onSelect={() => undefined}
          placeholder="Search sources"
        />
        <CommandSearch
          emptyLabel="No matches"
          items={[]}
          label="Search sessions"
          onSelect={() => undefined}
          placeholder="Search sessions"
        />
      </>,
    )

    expect(screen.getByRole('searchbox', { name: 'Search sources' }).getAttribute('id')).not.toBe(
      screen.getByRole('searchbox', { name: 'Search sessions' }).getAttribute('id'),
    )
  })
})

describe('InsightDeck', () => {
  test('pages within bounds and labels a caller-supplied trend from its insight title', async () => {
    const user = userEvent.setup()
    render(
      <InsightDeck
        insights={[
          {
            body: 'First body',
            id: 'first',
            title: 'First insight',
            trend: [
              { x: 0, y: 5 },
              { x: 2, y: 9 },
            ],
          },
          { body: 'Second body', id: 'second', title: 'Second insight' },
        ]}
        label="Operational insights"
      />,
    )

    expect(screen.getByRole('img', { name: 'First insight trend' })).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Previous insight' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
    await user.click(screen.getByRole('button', { name: 'Next insight' }))
    expect(screen.getByText('Second body')).toBeTruthy()
    expect((screen.getByRole('button', { name: 'Next insight' }) as HTMLButtonElement).disabled).toBe(
      true,
    )
  })

  test('does not render a trend graphic from fewer than two points', () => {
    render(
      <InsightDeck
        insights={[{ body: 'Body', id: 'one', title: 'Single point', trend: [{ x: 0, y: 1 }] }]}
        label="Operational insights"
      />,
    )

    expect(screen.queryByRole('img', { name: 'Single point trend' })).toBeNull()
  })

  test('uses only finite trend points and omits the graphic when fewer than two remain', () => {
    const { rerender } = render(
      <InsightDeck
        insights={[
          {
            body: 'Body',
            id: 'mixed',
            title: 'Mixed trend',
            trend: [
              { x: 0, y: 1 },
              { x: Number.NaN, y: 3 },
              { x: 1, y: Number.POSITIVE_INFINITY },
              { x: 2, y: 4 },
            ],
          },
        ]}
        label="Operational insights"
      />,
    )

    expect(screen.getByRole('img', { name: 'Mixed trend trend' }).querySelector('path')?.getAttribute('d')).not.toMatch(
      /NaN|Infinity/,
    )

    rerender(
      <InsightDeck
        insights={[
          {
            body: 'Body',
            id: 'invalid',
            title: 'Invalid trend',
            trend: [
              { x: Number.NaN, y: 1 },
              { x: 1, y: Number.NEGATIVE_INFINITY },
            ],
          },
        ]}
        label="Operational insights"
      />,
    )

    expect(screen.queryByRole('img', { name: 'Invalid trend trend' })).toBeNull()
  })

  test('renders a finite trend for constant coordinate ranges and an empty deck state', () => {
    const { rerender } = render(
      <InsightDeck
        insights={[
          {
            body: 'Body',
            id: 'constant',
            title: 'Constant trend',
            trend: [
              { x: 3, y: 5 },
              { x: 3, y: 5 },
            ],
          },
        ]}
        label="Operational insights"
      />,
    )

    expect(screen.getByRole('img', { name: 'Constant trend trend' }).querySelector('path')?.getAttribute('d')).not.toMatch(
      /NaN|Infinity/,
    )

    rerender(<InsightDeck insights={[]} label="Operational insights" />)

    expect(screen.getByText('No insights available.')).toBeTruthy()
  })
})

describe('ParameterTuner', () => {
  test('clamps numeric output to its bounds and preserves the supplied step', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(
      <ParameterTuner
        label="Retriever settings"
        onChange={onChange}
        parameters={[{ id: 'top-k', label: 'Top K', max: 10, min: 1, step: 2, value: 4 }]}
      />,
    )

    expect(
      screen.getByRole('group', { name: 'Retriever settings' }).getAttribute('data-slot'),
    ).toBe('parameter-tuner')
    expect(screen.queryByRole('region', { name: 'Retriever settings' })).toBeNull()
    const input = screen.getByRole('spinbutton', { name: 'Top K' })
    expect(input.getAttribute('step')).toBe('2')
    await user.clear(input)
    await user.type(input, '22')

    expect(onChange).toHaveBeenLastCalledWith('top-k', 10)
  })

  test('assigns distinct labelled inputs to multiple instances', () => {
    render(
      <>
        <ParameterTuner
          label="Retriever settings"
          onChange={() => undefined}
          parameters={[{ id: 'top-k', label: 'Top K', max: 10, min: 1, value: 4 }]}
        />
        <ParameterTuner
          label="Runtime settings"
          onChange={() => undefined}
          parameters={[{ id: 'top-k', label: 'Runtime Top K', max: 10, min: 1, value: 4 }]}
        />
      </>,
    )

    expect(screen.getByRole('spinbutton', { name: 'Top K' }).getAttribute('id')).not.toBe(
      screen.getByRole('spinbutton', { name: 'Runtime Top K' }).getAttribute('id'),
    )
  })
})
