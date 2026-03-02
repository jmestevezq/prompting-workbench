import { useState, useMemo } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { Transcript } from '../api/types'
import DataTable from './DataTable'
import StatusBadge from './StatusBadge'
import TagBadge from './TagBadge'

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
        className="flex items-center gap-1.5 text-[13px] font-medium text-indigo-600 hover:text-indigo-700 py-1.5 transition-colors"
      >
        {selectedIds.size} of {transcripts.length} transcripts
        {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {expanded && (
        <div className="mt-2">
          {allTags.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {allTags.map((tag) => {
                const selected = isTagFullySelected(tag)
                return (
                  <button
                    key={tag}
                    onClick={() => toggleTagChip(tag)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-all duration-150 font-medium ${
                      selected
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:border-indigo-400'
                    }`}
                  >
                    {tag} ({tagCounts[tag]})
                  </button>
                )
              })}
            </div>
          )}
          <div className="max-h-56 overflow-auto">
            <DataTable
              columns={[
                { key: 'name', header: 'Name', sortable: true },
                { key: 'source', header: 'Source', render: (r) => <StatusBadge status={(r as Transcript).source} /> },
                {
                  key: 'tags',
                  header: 'Tags',
                  render: (r) => {
                    const t = r as Transcript
                    const labels = t.labels ?? {}
                    return (
                      <div className="flex flex-wrap gap-1">
                        {(t.tags ?? []).map((tag) => (
                          <TagBadge key={tag} tag={tag} label={labels[tag]} />
                        ))}
                      </div>
                    )
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
