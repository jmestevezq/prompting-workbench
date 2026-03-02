import { useEffect, useRef, useState } from 'react'
import { useDevLogStore, selectFilteredEntries } from '../store/devLogStore'
import LogEntry from '../components/LogEntry'

const CATEGORIES = [
  'API_OUT', 'API_IN', 'API_ERR',
  'WS_OUT', 'WS_IN', 'WS_ERR',
  'GEMINI', 'TOOL', 'DB',
  'REQ', 'RES', 'ERR', 'WS', 'STATE',
]

const LEVELS = ['info', 'warn', 'error', 'debug'] as const

export default function DevLogs() {
  const store = useDevLogStore()
  const filtered = selectFilteredEntries(store)
  const { filters, isPaused, isConnected, clearLogs, setFilter, togglePause } = store

  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (autoScroll && !isPaused && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'instant' })
    }
  }, [filtered.length, autoScroll, isPaused])

  // Detect manual scroll up → disable auto-scroll
  function handleScroll() {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
  }

  const frontendCount = store.entries.filter((e) => e.source === 'frontend').length
  const backendCount = store.entries.filter((e) => e.source === 'backend').length

  return (
    <div className="h-full flex flex-col bg-slate-900 text-sm font-mono">
      {/* Filter bar */}
      <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-slate-700 flex-wrap shrink-0">
        {/* Source toggle */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-xs">
          {(['all', 'frontend', 'backend'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilter('source', s)}
              className={`px-2 py-1 capitalize transition-colors ${
                filters.source === s
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Level toggle */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-xs">
          <button
            onClick={() => setFilter('level', 'all')}
            className={`px-2 py-1 transition-colors ${
              filters.level === 'all'
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
            }`}
          >
            all
          </button>
          {LEVELS.map((l) => (
            <button
              key={l}
              onClick={() => setFilter('level', l)}
              className={`px-2 py-1 capitalize transition-colors ${
                filters.level === l
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700'
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        {/* Category dropdown */}
        <select
          value={filters.category}
          onChange={(e) => setFilter('category', e.target.value)}
          className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-indigo-500"
          aria-label="Filter by category"
        >
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>

        {/* Search */}
        <input
          type="text"
          placeholder="Search..."
          value={filters.search}
          onChange={(e) => setFilter('search', e.target.value)}
          className="text-xs bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-1 focus:outline-none focus:border-indigo-500 w-40"
          aria-label="Search logs"
        />

        <div className="flex-1" />

        {/* Pause */}
        <button
          onClick={togglePause}
          className={`text-xs px-2 py-1 rounded border transition-colors ${
            isPaused
              ? 'border-amber-600 bg-amber-950/60 text-amber-400'
              : 'border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
          }`}
        >
          {isPaused ? '▶ Resume' : '⏸ Pause'}
        </button>

        {/* Clear */}
        <button
          onClick={clearLogs}
          className="text-xs px-2 py-1 rounded border border-slate-700 text-slate-400 hover:text-rose-400 hover:border-rose-800 transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Log area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto py-1"
      >
        {filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-600 text-xs">
            {store.entries.length === 0 ? 'Waiting for log entries…' : 'No entries match the current filters.'}
          </div>
        ) : (
          filtered.map((entry) => (
            <LogEntry key={entry.id} entry={entry} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-4 px-3 py-1.5 bg-slate-800 border-t border-slate-700 text-[11px] text-slate-500 shrink-0">
        <span>{filtered.length} / {store.entries.length} entries</span>
        <span>FE: {frontendCount}</span>
        <span>BE: {backendCount}</span>
        <div className="flex-1" />
        <span className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`} aria-hidden />
          <span>{isConnected ? 'SSE Connected' : 'SSE Disconnected'}</span>
        </span>
      </div>
    </div>
  )
}
