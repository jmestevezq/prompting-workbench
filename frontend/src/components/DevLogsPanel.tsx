import { useEffect, useRef, useState } from 'react'
import { X, Minus, Terminal } from 'lucide-react'
import { useDevLogStore, selectFilteredEntries } from '../store/devLogStore'
import LogEntry from './LogEntry'

const CATEGORIES = [
  'API_OUT', 'API_IN', 'API_ERR',
  'WS_OUT', 'WS_IN', 'WS_ERR',
  'GEMINI', 'TOOL', 'DB',
  'REQ', 'RES', 'ERR', 'WS', 'STATE',
]

const LEVELS = ['info', 'warn', 'error', 'debug'] as const

export default function DevLogsPanel() {
  const store = useDevLogStore()
  const filtered = selectFilteredEntries(store)
  const { filters, isPaused, isConnected, isPanelOpen, clearLogs, setFilter, togglePause, togglePanel } = store

  const bottomRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    if (autoScroll && !isPaused && isPanelOpen && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: 'instant' })
    }
  }, [filtered.length, autoScroll, isPaused, isPanelOpen])

  function handleScroll() {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    setAutoScroll(atBottom)
  }

  const unreadCount = store.entries.length

  if (!isPanelOpen) return null

  return (
    <div
      className="fixed bottom-0 left-14 right-0 h-[50vh] bg-slate-900 border-t border-slate-700 flex flex-col z-40 shadow-2xl"
      style={{ transition: 'height 0.15s ease' }}
    >
      {/* Header bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 border-b border-slate-700 shrink-0">
        <Terminal size={13} className="text-indigo-400 shrink-0" />
        <span className="text-[12px] font-semibold text-slate-300">Developer Console</span>

        {/* Source toggle */}
        <div className="flex rounded overflow-hidden border border-slate-700 text-[10px] ml-3">
          {(['all', 'frontend', 'backend'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setFilter('source', s)}
              className={`px-2 py-0.5 capitalize transition-colors ${
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
        <div className="flex rounded overflow-hidden border border-slate-700 text-[10px]">
          <button
            onClick={() => setFilter('level', 'all')}
            className={`px-2 py-0.5 transition-colors ${
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
              className={`px-2 py-0.5 capitalize transition-colors ${
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
          className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 rounded px-1.5 py-0.5 focus:outline-none focus:border-indigo-500"
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
          placeholder="Search…"
          value={filters.search}
          onChange={(e) => setFilter('search', e.target.value)}
          className="text-[10px] bg-slate-800 border border-slate-700 text-slate-300 rounded px-2 py-0.5 focus:outline-none focus:border-indigo-500 w-32"
          aria-label="Search logs"
        />

        <div className="flex-1" />

        {/* Entry count */}
        <span className="text-[10px] text-slate-500 tabular-nums">
          {filtered.length}/{unreadCount}
        </span>

        {/* SSE status dot */}
        <span
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${isConnected ? 'bg-emerald-500' : 'bg-rose-500'}`}
          title={isConnected ? 'SSE Connected' : 'SSE Disconnected'}
        />

        {/* Pause */}
        <button
          onClick={togglePause}
          title={isPaused ? 'Resume' : 'Pause'}
          className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors ${
            isPaused
              ? 'border-amber-600 bg-amber-950/60 text-amber-400'
              : 'border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-700'
          }`}
        >
          {isPaused ? '▶' : '⏸'}
        </button>

        {/* Clear */}
        <button
          onClick={clearLogs}
          title="Clear logs"
          className="text-[10px] px-1.5 py-0.5 rounded border border-slate-700 text-slate-400 hover:text-rose-400 hover:border-rose-800 transition-colors"
        >
          Clear
        </button>

        {/* Close / minimize */}
        <button
          onClick={togglePanel}
          title="Close console"
          className="ml-1 text-slate-400 hover:text-slate-200 transition-colors"
          aria-label="Close developer console"
        >
          <X size={14} />
        </button>
      </div>

      {/* Log area */}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto font-mono text-[12px] py-0.5"
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
    </div>
  )
}
