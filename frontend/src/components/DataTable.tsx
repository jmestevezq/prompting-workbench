import { useState } from 'react'

interface Column<T> {
  key: string
  header: string
  render?: (row: T) => React.ReactNode
  sortable?: boolean
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  onRowClick?: (row: T) => void
  keyField?: string
  emptyMessage?: string
}

export default function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  onRowClick,
  keyField = 'id',
  emptyMessage = 'No data',
}: DataTableProps<T>) {
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

  if (!data.length) {
    return <div className="text-center py-8 text-gray-400 text-sm">{emptyMessage}</div>
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
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
          {sorted.map((row) => (
            <tr
              key={String(row[keyField])}
              className={`border-b border-gray-100 ${onRowClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className="px-3 py-2 text-gray-800">
                  {col.render ? col.render(row) : String(row[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
