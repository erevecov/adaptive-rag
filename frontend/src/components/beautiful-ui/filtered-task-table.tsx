import { RecordsGrid, type RecordsGridColumn } from './records-grid'

export type FilterOption = { id: string; label: string }

export type FilteredTaskTableProps<Row extends { id: string }> = {
  activeFilter: string
  columns: readonly RecordsGridColumn<Row>[]
  emptyLabel: string
  filters: readonly FilterOption[]
  label: string
  onFilterChange(id: string): void
  rows: readonly Row[]
}

export function FilteredTaskTable<Row extends { id: string }>({
  activeFilter,
  columns,
  emptyLabel,
  filters,
  label,
  onFilterChange,
  rows,
}: FilteredTaskTableProps<Row>) {
  return (
    <section aria-label={label} className="grid gap-2" data-slot="filtered-task-table">
      <div aria-label={`${label} filters`} className="flex flex-wrap gap-2" role="group">
        {filters.map((filter) => (
          <button
            aria-pressed={filter.id === activeFilter}
            className="min-h-9 rounded-[2px] border border-border px-3 text-sm motion-safe:transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring max-[680px]:min-h-11"
            data-active={filter.id === activeFilter ? '' : undefined}
            key={filter.id}
            onClick={() => onFilterChange(filter.id)}
            type="button"
          >
            {filter.label}
          </button>
        ))}
      </div>
      <RecordsGrid columns={columns} emptyLabel={emptyLabel} label={label} rows={rows} />
    </section>
  )
}
