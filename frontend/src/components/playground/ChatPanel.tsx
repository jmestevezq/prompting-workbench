import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Turn, ToolCall } from '../../api/types'

interface ChatMessage {
  id?: string
  role: 'user' | 'agent' | 'tool_call' | 'tool_response' | 'system'
  content: string
  toolCall?: ToolCall
  toolResult?: unknown
  turnData?: Turn
  streaming?: boolean
}

interface ChatPanelProps {
  messages: ChatMessage[]
  onSendMessage: (content: string) => void
  onSelectTurn: (turn: Turn | null) => void
  isStreaming: boolean
  wsConnected: boolean
  sessionActive: boolean
}

export default function ChatPanel({
  messages,
  onSendMessage,
  onSelectTurn,
  isStreaming,
  wsConnected,
  sessionActive,
}: ChatPanelProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return
    onSendMessage(input.trim())
    setInput('')
  }

  return (
    <div className="flex flex-col border-r border-slate-200 bg-white overflow-hidden">
      {/* Status bar */}
      <div className="px-4 py-2 border-b border-slate-200 flex items-center gap-2 text-xs text-slate-500">
        <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400' : 'bg-slate-300'}`} />
        {sessionActive ? (wsConnected ? 'Connected' : 'Disconnected') : 'No session'}
        {isStreaming && <span className="text-indigo-600 ml-2">Generating...</span>}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!sessionActive && (
          <div className="text-center text-slate-400 text-sm mt-16">
            Select an agent to start chatting
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            message={msg}
            onClick={() => {
              if (msg.turnData) onSelectTurn(msg.turnData)
            }}
            onSendMessage={onSendMessage}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-slate-200">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={sessionActive ? 'Type a message...' : 'Select an agent first'}
            disabled={!sessionActive || isStreaming}
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
          />
          <button
            type="submit"
            disabled={!sessionActive || isStreaming || !input.trim()}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

// ── Renderable block types ──────────────────────────────────────────

type RenderableBlock =
  | { type: 'promptSuggestions'; suggestions: string[] }
  | { type: 'pieChart'; slices: { label: string; value: number }[] }
  | { type: 'lineChart'; dataPoints: { x: string; y: number }[] }
  | { type: 'table'; title?: string; headers: { text: string }[]; rows: { cells: { textCell: { text: string } }[] }[] }

const WIDGET_KEYS = ['promptSuggestionsBlock', 'pieChartBlock', 'lineChartBlock', 'tableBlock'] as const

function extractBlocks(parsed: Record<string, unknown>): RenderableBlock[] {
  const blocks: RenderableBlock[] = []
  if (parsed?.promptSuggestionsBlock && (parsed.promptSuggestionsBlock as { suggestions?: string[] }).suggestions) {
    blocks.push({ type: 'promptSuggestions', suggestions: (parsed.promptSuggestionsBlock as { suggestions: string[] }).suggestions })
  }
  if (parsed?.pieChartBlock && (parsed.pieChartBlock as { slices?: unknown[] }).slices) {
    blocks.push({ type: 'pieChart', slices: (parsed.pieChartBlock as { slices: { label: string; value: number }[] }).slices })
  }
  if (parsed?.lineChartBlock && (parsed.lineChartBlock as { dataPoints?: unknown[] }).dataPoints) {
    blocks.push({ type: 'lineChart', dataPoints: (parsed.lineChartBlock as { dataPoints: { x: string; y: number }[] }).dataPoints })
  }
  if (parsed?.tableBlock) {
    const tb = parsed.tableBlock as { title?: string; headers?: { text: string }[]; rows?: { cells: { textCell: { text: string } }[] }[] }
    if (tb.headers && tb.rows) {
      blocks.push({ type: 'table', title: tb.title, headers: tb.headers, rows: tb.rows })
    }
  }
  return blocks
}

function tryParseRenderableBlocks(content: string): { blocks: RenderableBlock[]; textParts: string[] } | null {
  const blocks: RenderableBlock[] = []
  const textParts: string[] = []

  // Try parsing the entire content as JSON first
  try {
    const parsed = JSON.parse(content)
    const found = extractBlocks(parsed)
    if (found.length > 0) return { blocks: found, textParts }
  } catch {
    // Not pure JSON — look for embedded JSON blocks
  }

  // Match ```json ... ``` fenced blocks or bare JSON containing any widget key
  const keyPattern = WIDGET_KEYS.join('|')
  const jsonBlockRegex = new RegExp(
    '```json\\s*\\n?([\\s\\S]*?)\\n?\\s*```|(\\{[\\s\\S]*?(?:' + keyPattern + ')[\\s\\S]*?\\}(?:\\s*\\}))',
    'g',
  )
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = jsonBlockRegex.exec(content)) !== null) {
    const before = content.slice(lastIndex, match.index).trim()
    if (before) textParts.push(before)
    lastIndex = match.index + match[0].length

    const jsonStr = match[1] ?? match[2]
    try {
      const parsed = JSON.parse(jsonStr)
      blocks.push(...extractBlocks(parsed))
    } catch {
      textParts.push(match[0])
    }
  }

  const remaining = content.slice(lastIndex).trim()
  if (remaining) textParts.push(remaining)

  if (blocks.length === 0) return null
  return { blocks, textParts }
}

// ── Widget renderers ────────────────────────────────────────────────

const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981',
  '#ef4444', '#06b6d4', '#f97316', '#6366f1', '#14b8a6',
]

function PromptSuggestionChips({
  suggestions,
  onSuggestionClick,
}: {
  suggestions: string[]
  onSuggestionClick?: (text: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((suggestion, i) => (
        <button
          key={i}
          onClick={(e) => {
            e.stopPropagation()
            onSuggestionClick?.(suggestion)
          }}
          className="group/chip relative text-left px-4 py-2.5 rounded-2xl border border-slate-200 bg-white text-sm text-slate-700 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 transition-all duration-150 shadow-xs hover:shadow cursor-pointer max-w-[320px]"
        >
          <span className="line-clamp-2">{suggestion}</span>
          <svg
            className="inline-block ml-1.5 w-3.5 h-3.5 text-slate-300 group-hover/chip:text-indigo-400 transition-colors shrink-0"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
      ))}
    </div>
  )
}

function PieChartWidget({ slices }: { slices: { label: string; value: number }[] }) {
  const total = slices.reduce((sum, s) => sum + s.value, 0)
  if (total === 0) return null

  const size = 160
  const cx = size / 2
  const cy = size / 2
  const r = 60

  let cumAngle = -Math.PI / 2
  const arcs = slices.map((slice, i) => {
    const angle = (slice.value / total) * 2 * Math.PI
    const startX = cx + r * Math.cos(cumAngle)
    const startY = cy + r * Math.sin(cumAngle)
    cumAngle += angle
    const endX = cx + r * Math.cos(cumAngle)
    const endY = cy + r * Math.sin(cumAngle)
    const largeArc = angle > Math.PI ? 1 : 0
    const d = `M ${cx} ${cy} L ${startX} ${startY} A ${r} ${r} 0 ${largeArc} 1 ${endX} ${endY} Z`
    return { d, color: CHART_COLORS[i % CHART_COLORS.length], label: slice.label, value: slice.value, pct: ((slice.value / total) * 100).toFixed(1) }
  })

  return (
    <div className="flex items-start gap-4">
      <svg width={size} height={size} className="shrink-0">
        {arcs.map((arc, i) => (
          <path key={i} d={arc.d} fill={arc.color} stroke="white" strokeWidth={1.5}>
            <title>{arc.label}: {arc.pct}%</title>
          </path>
        ))}
      </svg>
      <div className="flex flex-col gap-1 text-xs pt-1 min-w-0">
        {arcs.map((arc, i) => (
          <div key={i} className="flex items-center gap-1.5 min-w-0">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: arc.color }} />
            <span className="truncate text-slate-700">{arc.label}</span>
            <span className="text-slate-400 ml-auto shrink-0">{arc.pct}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function LineChartWidget({ dataPoints }: { dataPoints: { x: string; y: number }[] }) {
  if (dataPoints.length === 0) return null

  const w = 280
  const h = 140
  const pad = { top: 12, right: 12, bottom: 28, left: 48 }
  const plotW = w - pad.left - pad.right
  const plotH = h - pad.top - pad.bottom

  const yValues = dataPoints.map((d) => d.y)
  const yMin = Math.min(...yValues)
  const yMax = Math.max(...yValues)
  const yRange = yMax - yMin || 1

  const points = dataPoints.map((d, i) => ({
    x: pad.left + (i / Math.max(dataPoints.length - 1, 1)) * plotW,
    y: pad.top + plotH - ((d.y - yMin) / yRange) * plotH,
    label: d.x,
    value: d.y,
  }))

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
  const areaPath = linePath + ` L ${points[points.length - 1].x} ${pad.top + plotH} L ${points[0].x} ${pad.top + plotH} Z`

  // Y-axis ticks (3 ticks)
  const yTicks = [yMin, yMin + yRange / 2, yMax].map((v) => ({
    value: v,
    y: pad.top + plotH - ((v - yMin) / yRange) * plotH,
    label: v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v.toFixed(0),
  }))

  return (
    <svg width={w} height={h} className="overflow-visible">
      {/* Grid lines */}
      {yTicks.map((t, i) => (
        <g key={i}>
          <line x1={pad.left} y1={t.y} x2={w - pad.right} y2={t.y} stroke="#e5e7eb" strokeWidth={1} />
          <text x={pad.left - 6} y={t.y + 3} textAnchor="end" className="text-[9px] fill-slate-400">{t.label}</text>
        </g>
      ))}
      {/* Area fill */}
      <path d={areaPath} fill="#6366f1" opacity={0.08} />
      {/* Line */}
      <path d={linePath} fill="none" stroke="#6366f1" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
      {/* Dots + X labels */}
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={p.x} cy={p.y} r={3} fill="white" stroke="#6366f1" strokeWidth={1.5}>
            <title>{p.label}: {p.value}</title>
          </circle>
          <text x={p.x} y={h - 6} textAnchor="middle" className="text-[9px] fill-slate-500">{p.label}</text>
        </g>
      ))}
    </svg>
  )
}

function TableWidget({
  title,
  headers,
  rows,
}: {
  title?: string
  headers: { text: string }[]
  rows: { cells: { textCell: { text: string } }[] }[]
}) {
  return (
    <div className="overflow-auto">
      {title && <div className="text-xs font-semibold text-slate-700 mb-1.5">{title}</div>}
      <table className="text-xs border-collapse w-full">
        <thead>
          <tr>
            {headers.map((h, i) => (
              <th key={i} className="px-2.5 py-1.5 text-left font-semibold text-slate-600 bg-slate-200/70 border border-slate-300 whitespace-nowrap">
                {h.text}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
              {row.cells.map((cell, ci) => (
                <td key={ci} className="px-2.5 py-1.5 border border-slate-200 text-slate-700 whitespace-nowrap">
                  {cell.textCell?.text ?? ''}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function MessageBubble({
  message,
  onClick,
  onSendMessage,
}: {
  message: ChatMessage
  onClick?: () => void
  onSendMessage?: (content: string) => void
}) {
  const { role, content, toolCall, streaming } = message
  const [showRaw, setShowRaw] = useState(false)
  // For renderable blocks: false = rendered view (default), true = JSON view
  const [showJson, setShowJson] = useState(false)

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-indigo-600 text-white rounded-2xl px-3 py-2 max-w-[80%] text-sm">
          {content}
        </div>
      </div>
    )
  }

  if (role === 'agent') {
    // While streaming: show plain text with cursor — no markdown parsing, no widget detection
    if (streaming) {
      return (
        <div className="flex gap-2">
          <div className="bg-slate-100 rounded-2xl px-3 py-2 max-w-[85%] text-sm">
            <span className="whitespace-pre-wrap text-slate-800">{content}</span>
            <span className="inline-block w-1.5 h-4 bg-indigo-500 animate-pulse ml-0.5 align-middle" />
          </div>
        </div>
      )
    }

    // After complete: try to parse widget blocks
    const parsed = tryParseRenderableBlocks(content)

    // If we have renderable blocks, show rendered/json toggle
    if (parsed) {
      return (
        <div className="group flex gap-2" onClick={onClick}>
          <div className="bg-slate-100 rounded-2xl px-3 py-2 max-w-[85%] text-sm">
            {/* Text parts before/around blocks */}
            {!showJson && parsed.textParts.length > 0 && (
              <div className="prose prose-sm prose-slate max-w-none mb-2">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.textParts.join('\n\n')}</ReactMarkdown>
              </div>
            )}

            {showJson ? (
              <>
                <pre className="whitespace-pre-wrap text-xs font-mono text-slate-700 overflow-auto">{content}</pre>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowJson(false) }}
                  className="mt-2 text-[10px] text-indigo-500 hover:text-indigo-700 font-medium"
                >
                  raw message toggle
                </button>
              </>
            ) : (
              <>
                <div className="space-y-3">
                  {parsed.blocks.map((block, i) => (
                    <div key={i}>
                      {block.type === 'promptSuggestions' && (
                        <PromptSuggestionChips
                          suggestions={block.suggestions}
                          onSuggestionClick={onSendMessage}
                        />
                      )}
                      {block.type === 'pieChart' && (
                        <PieChartWidget slices={block.slices} />
                      )}
                      {block.type === 'lineChart' && (
                        <LineChartWidget dataPoints={block.dataPoints} />
                      )}
                      {block.type === 'table' && (
                        <TableWidget title={block.title} headers={block.headers} rows={block.rows} />
                      )}
                    </div>
                  ))}
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowJson(true) }}
                  className="mt-2 text-[10px] text-indigo-500 hover:text-indigo-700 font-medium"
                >
                  raw message toggle
                </button>
              </>
            )}
          </div>
          {message.turnData && (
            <button
              className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-600 text-xs self-start mt-1"
              title="Inspect turn"
            >
              inspect
            </button>
          )}
        </div>
      )
    }

    // Default: markdown rendering with raw toggle
    return (
      <div className="group flex gap-2" onClick={onClick}>
        <div className="bg-slate-100 rounded-2xl px-3 py-2 max-w-[85%] text-sm">
          {showRaw ? (
            <pre className="whitespace-pre-wrap text-xs font-mono text-slate-700 overflow-auto">{content}</pre>
          ) : (
            <div className="prose prose-sm prose-slate max-w-none prose-table:text-xs prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-th:bg-slate-200 prose-table:border-collapse prose-th:border prose-th:border-slate-300 prose-td:border prose-td:border-slate-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
          {content && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowRaw(!showRaw) }}
              className="mt-1 text-[10px] text-slate-400 hover:text-slate-600"
            >
              {showRaw ? 'rendered' : 'raw'}
            </button>
          )}
        </div>
        {message.turnData && (
          <button
            className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-600 text-xs self-start mt-1"
            title="Inspect turn"
          >
            inspect
          </button>
        )}
      </div>
    )
  }

  if (role === 'tool_call') {
    return (
      <details className="bg-amber-50 border border-amber-200 rounded-lg text-xs overflow-hidden">
        <summary className="px-3 py-1.5 cursor-pointer text-amber-700 font-medium">
          Tool Call: {toolCall?.name ?? 'unknown'}
        </summary>
        <pre className="px-3 py-2 bg-amber-50 text-amber-800 overflow-auto max-h-40">
          {toolCall ? JSON.stringify(toolCall.args, null, 2) : content}
        </pre>
      </details>
    )
  }

  if (role === 'tool_response') {
    return (
      <details className="bg-emerald-50 border border-emerald-200 rounded-lg text-xs overflow-hidden">
        <summary className="px-3 py-1.5 cursor-pointer text-emerald-700 font-medium">
          Tool Response
        </summary>
        <pre className="px-3 py-2 bg-emerald-50 text-emerald-800 overflow-auto max-h-40">
          {content}
        </pre>
      </details>
    )
  }

  if (role === 'system') {
    return (
      <div className="text-center text-xs text-slate-400 py-1">{content}</div>
    )
  }

  return null
}
