import { useState, useEffect, useRef, useMemo } from 'react'

interface TagEditorProps {
  tags: string[]
  onChange: (tags: string[]) => void
  suggestions: string[]
}

export default function TagEditor({ tags, onChange, suggestions }: TagEditorProps) {
  const [input, setInput] = useState('')
  const [showSuggestions, setShowSuggestions] = useState(false)
  const wrapperRef = useRef<HTMLDivElement>(null)

  const filtered = useMemo(() => {
    if (!input.trim()) return []
    const q = input.trim().toLowerCase()
    return suggestions.filter((s) => s.includes(q) && !tags.includes(s)).slice(0, 6)
  }, [input, suggestions, tags])

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const addTag = (tag: string) => {
    const t = tag.trim().toLowerCase()
    if (t && !tags.includes(t)) onChange([...tags, t])
    setInput('')
    setShowSuggestions(false)
  }

  return (
    <div ref={wrapperRef} className="relative flex flex-wrap items-center gap-1">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-0.5 text-xs bg-indigo-50 text-indigo-600 rounded px-1.5 py-0.5"
        >
          {tag}
          <button
            onClick={() => onChange(tags.filter((t) => t !== tag))}
            className="text-indigo-400 hover:text-indigo-700 ml-0.5"
          >
            &times;
          </button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => { setInput(e.target.value); setShowSuggestions(true) }}
        onFocus={() => setShowSuggestions(true)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.preventDefault(); addTag(input) }
        }}
        placeholder="Add tag..."
        className="text-xs border border-slate-200 rounded px-1.5 py-0.5 w-24 focus:outline-none focus:border-indigo-400"
      />
      {showSuggestions && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 bg-white border border-slate-200 rounded shadow-md z-10 min-w-[120px]">
          {filtered.map((s) => (
            <button
              key={s}
              onClick={() => addTag(s)}
              className="block w-full text-left text-xs px-2 py-1 hover:bg-indigo-50 text-slate-700"
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
