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
    return <div className="text-center py-8 text-gray-400 text-sm">{emptyMessage}</div>
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            {selectable && (
              <th className="px-3 py-2 w-8">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => { if (el) el.indeterminate = !!someSelected }}
                  onChange={toggleAll}
                  className="rounded border-gray-300"
                />
              </th>
            )}
            {columns.map((col) => (
              <th
                key={col.key}
                className={`text-left px-3 py-2 font-medium text-gray-600 ${col.sortable ? 'cursor-pointer hover:text-gray-900 select-none' : ''}`}
                onClick={col.sortable ? () => handleSort(col.key) : undefined}
              >
                {col.header}
                {sortKey === col.key && (sortDir === 'asc' ? ' ↑' : ' ↓')}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row) => {
            const rowId = String(row[keyField])
            return (
              <tr
                key={rowId}
                className={`border-b border-gray-100 ${onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {selectable && (
                  <td className="px-3 py-2 w-8">
                    <input
                      type="checkbox"
                      checked={selectedIds?.has(rowId) ?? false}
                      onChange={() => toggleRow(rowId)}
                      onClick={(e) => e.stopPropagation()}
                      className="rounded border-gray-300"
                    />
                  </td>
                )}
                {columns.map((col) => (
                  <td key={col.key} className="px-3 py-2 text-gray-800">
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
