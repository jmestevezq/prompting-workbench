import { useState, useMemo } from 'react'
import type { Transcript } from '../api/types'
import DataTable from './DataTable'
import StatusBadge from './StatusBadge'

interface TranscriptPickerProps {
  transcripts: Transcript[]
  selectedIds: Set<string>
  onSelectionChange: (ids: Set<string>) => void
}

export default function TranscriptPicker({
  transcripts,
  selectedIds,
  onSelectionChange,
}: TranscriptPickerProps) {
  const [expanded, setExpanded] = useState(false)

  const allTags = useMemo(
    () => Array.from(new Set(transcripts.flatMap((t) => t.tags ?? []))),
    [transcripts],
  )

  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const t of transcripts) {
      for (const tag of t.tags ?? []) {
        counts[tag] = (counts[tag] ?? 0) + 1
      }
    }
    return counts
  }, [transcripts])

  const isTagFullySelected = (tag: string) => {
    const idsWithTag = transcripts
      .filter((t) => (t.tags ?? []).includes(tag))
      .map((t) => t.id)
    return idsWithTag.length > 0 && idsWithTag.every((id) => selectedIds.has(id))
  }

  const toggleTagChip = (tag: string) => {
    const idsWithTag = transcripts
      .filter((t) => (t.tags ?? []).includes(tag))
      .map((t) => t.id)
    const allSelected = idsWithTag.every((id) => selectedIds.has(id))
    const next = new Set(selectedIds)
    if (allSelected) {
      idsWithTag.forEach((id) => next.delete(id))
    } else {
      idsWithTag.forEach((id) => next.add(id))
    }
    onSelectionChange(next)
  }

  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-blue-600 hover:text-blue-800 py-1.5"
      >
        {selectedIds.size} of {transcripts.length} transcripts {expanded ? '▲' : '▼'}
      </button>

      {expanded && (
        <div className="mt-2">
          {allTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-2">
              {allTags.map((tag) => {
                const selected = isTagFullySelected(tag)
                return (
                  <button
                    key={tag}
                    onClick={() => toggleTagChip(tag)}
                    className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                      selected
                        ? 'bg-blue-500 text-white border-blue-500'
                        : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                    }`}
                  >
                    {tag} ({tagCounts[tag]})
                  </button>
                )
              })}
            </div>
          )}
          <div className="border border-gray-200 rounded max-h-56 overflow-auto">
            <DataTable
              columns={[
                { key: 'name', header: 'Name', sortable: true },
                { key: 'source', header: 'Source', render: (r) => <StatusBadge status={(r as Transcript).source} /> },
                {
                  key: 'tags',
                  header: 'Tags',
                  render: (r) => {
                    const t = r as Transcript
                    return (t.tags ?? []).map((tag) => (
                      <span key={tag} className="inline-block mr-1 text-xs bg-blue-50 text-blue-600 rounded px-1">
                        {tag}
                      </span>
                    ))
                  },
                },
              ]}
              data={transcripts}
              selectable
              selectedIds={selectedIds}
              onSelectionChange={onSelectionChange}
            />
          </div>
        </div>
      )}
    </div>
  )
}
