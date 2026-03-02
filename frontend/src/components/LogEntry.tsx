import { memo, useState } from 'react'
import type { DevLogEntry } from '../lib/devlog'

// Category → color mapping
const CATEGORY_STYLES: Record<string, { text: string; badge: string }> = {
  API_OUT: { text: 'text-indigo-400', badge: 'bg-indigo-950/60' },
  REQ:     { text: 'text-indigo-400', badge: 'bg-indigo-950/60' },
  API_IN:  { text: 'text-emerald-400', badge: 'bg-emerald-950/60' },
  RES:     { text: 'text-emerald-400', badge: 'bg-emerald-950/60' },
  API_ERR: { text: 'text-rose-400', badge: 'bg-rose-950/60' },
  ERR:     { text: 'text-rose-400', badge: 'bg-rose-950/60' },
  WS_OUT:  { text: 'text-violet-400', badge: 'bg-violet-950/60' },
  WS_IN:   { text: 'text-teal-400', badge: 'bg-teal-950/60' },
  WS_ERR:  { text: 'text-rose-400', badge: 'bg-rose-950/60' },
  GEMINI:  { text: 'text-violet-400', badge: 'bg-violet-950/60' },
  TOOL:    { text: 'text-cyan-400', badge: 'bg-cyan-950/60' },
  DB:      { text: 'text-amber-400', badge: 'bg-amber-950/60' },
  STATE:   { text: 'text-amber-400', badge: 'bg-amber-950/60' },
  WS:      { text: 'text-violet-400', badge: 'bg-violet-950/60' },
}

const LEVEL_TEXT: Record<string, string> = {
  error: 'text-rose-400',
  warn: 'text-amber-400',
  info: 'text-slate-200',
  debug: 'text-slate-500',
}

function formatTimestamp(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', fractionalSecondDigits: 3 })
  } catch {
    return iso
  }
}

interface LogEntryProps {
  entry: DevLogEntry
}

function LogEntryComponent({ entry }: LogEntryProps) {
  const [expanded, setExpanded] = useState(false)
  const styles = CATEGORY_STYLES[entry.category] ?? { text: 'text-slate-400', badge: 'bg-slate-800' }
  const msgColor = LEVEL_TEXT[entry.level] ?? 'text-slate-200'
  const hasDetails = entry.details !== undefined && entry.details !== null

  return (
    <div
      className={`group px-3 py-0.5 hover:bg-slate-800/40 ${hasDetails ? 'cursor-pointer' : ''}`}
      onClick={hasDetails ? () => setExpanded((v) => !v) : undefined}
      role={hasDetails ? 'button' : undefined}
      aria-expanded={hasDetails ? expanded : undefined}
    >
      <div className="flex items-baseline gap-2 min-w-0">
        <span className="text-slate-500 shrink-0 tabular-nums text-[11px]">
          {formatTimestamp(entry.timestamp)}
        </span>
        <span className={`shrink-0 text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded ${styles.text} ${styles.badge}`}>
          {entry.category}
        </span>
        <span className={`text-[12px] font-mono truncate ${msgColor}`}>
          {entry.message}
        </span>
        {hasDetails && (
          <span className="text-slate-600 text-[10px] shrink-0 ml-auto opacity-0 group-hover:opacity-100 select-none">
            {expanded ? '▲' : '▼'}
          </span>
        )}
      </div>
      {expanded && hasDetails && (
        <pre className="mt-1 ml-28 text-[11px] text-slate-400 font-mono overflow-x-auto pb-1 whitespace-pre-wrap break-words">
          {JSON.stringify(entry.details, null, 2)}
        </pre>
      )}
    </div>
  )
}

export default memo(LogEntryComponent)
