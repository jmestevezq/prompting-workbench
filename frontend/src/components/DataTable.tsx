import { useState } from 'react'

interface Column {
  key: string
  header: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  render?: (row: any) => React.ReactNode
  sortable?: boolean
}

interface DataTableProps {
  columns: Column[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  onRowClick?: (row: any) => void
  keyField?: string
  emptyMessage?: string
  selectable?: boolean
  selectedIds?: Set<string>
  onSelectionChange?: (ids: Set<string>) => void
}

export default function DataTable({
  columns,
  data,
  onRowClick,
  keyField = 'id',
  emptyMessage = 'No data',
  selectable,
  selectedIds,
  onSelectionChange,
}: DataTableProps) {
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc')

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = sortKey
    ? [...data].sort((a, b) => {
        const av = a[sortKey]
        const bv = b[sortKey]
        const cmp = String(av ?? '').localeCompare(String(bv ?? ''))
        return sortDir === 'asc' ? cmp : -cmp
      })
    : data

  const allSelected = selectable && data.length > 0 && selectedIds?.size === data.length
  const someSelected = selectable && selectedIds && selectedIds.size > 0 && selectedIds.size < data.length

  const toggleAll = () => {
    if (!onSelectionChange) return
    if (allSelected) {
      onSelectionChange(new Set())
    } else {
      onSelectionChange(new Set(data.map((row) => String(row[keyField]))))
    }
  }

  const toggleRow = (id: string) => {
    if (!onSelectionChange || !selectedIds) return
    const next = new Set(selectedIds)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    onSelectionChange(next)
  }

  if (!data.length) {
    return <div className="text-center py-8 text-slate-400 text-sm">{emptyMessage}</div>
  }

  return (
    <div className="overflow-auto rounded-lg border border-slate-200 shadow-xs">
      <table className="w-full text-[13px]">
        <thead>
          <tr className="bg-slate-50 border-b border-slate-200">
            {selectable && (
              <th className="px-4 py-2.5 w-8">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => { if (el) el.indeterminate = !!someSelected }}
                  onChange={toggleAll}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                className={`text-left px-4 py-2.5 text-xs uppercase tracking-wider font-medium text-slate-500 ${col.sortable ? 'cursor-pointer hover:text-slate-700 select-none' : ''}`}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                {col.header}
                {sortKey === col.key && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white">
          {sorted.map((row) => {
            const rowId = String(row[keyField])
            const isSelected = selectedIds?.has(rowId)
            return (
              <tr
                key={rowId}
                className={`border-b border-slate-100 transition-colors duration-100 ${
                  isSelected
                    ? 'bg-indigo-50 border-l-2 border-l-indigo-500'
                    : onRowClick
                      ? 'cursor-pointer hover:bg-indigo-50/50'
                      : ''
                }`}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {selectable && (
                  <td className="px-4 py-3 w-8">
                    <input
                      type="checkbox"
                      checked={isSelected ?? false}
                      onChange={() => toggleRow(rowId)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                    />
                  </td>
                )}
                {columns.map((col) => (
                  <td key={col.key} className="px-4 py-3 text-slate-700">
                    {col.render ? col.render(row) : String(row[col.key] ?? '')}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
