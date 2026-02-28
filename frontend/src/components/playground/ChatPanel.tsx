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
    <div className="flex flex-col border-r border-gray-200 bg-white overflow-hidden">
      {/* Status bar */}
      <div className="px-4 py-2 border-b border-gray-200 flex items-center gap-2 text-xs text-gray-500">
        <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400' : 'bg-gray-300'}`} />
        {sessionActive ? (wsConnected ? 'Connected' : 'Disconnected') : 'No session'}
        {isStreaming && <span className="text-blue-600 ml-2">Generating...</span>}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {!sessionActive && (
          <div className="text-center text-gray-400 text-sm mt-16">
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
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={sessionActive ? 'Type a message...' : 'Select an agent first'}
            disabled={!sessionActive || isStreaming}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
          />
          <button
            type="submit"
            disabled={!sessionActive || isStreaming || !input.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  )
}

function MessageBubble({
  message,
  onClick,
}: {
  message: ChatMessage
  onClick?: () => void
}) {
  const { role, content, toolCall, streaming } = message
  const [showRaw, setShowRaw] = useState(false)

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-blue-600 text-white rounded-lg px-3 py-2 max-w-[80%] text-sm">
          {content}
        </div>
      </div>
    )
  }

  if (role === 'agent') {
    return (
      <div className="group flex gap-2" onClick={onClick}>
        <div className="bg-gray-100 rounded-lg px-3 py-2 max-w-[85%] text-sm">
          {showRaw ? (
            <pre className="whitespace-pre-wrap text-xs font-mono text-gray-700 overflow-auto">{content}</pre>
          ) : (
            <div className="prose prose-sm prose-gray max-w-none prose-table:text-xs prose-th:px-2 prose-th:py-1 prose-td:px-2 prose-td:py-1 prose-th:bg-gray-200 prose-table:border-collapse prose-th:border prose-th:border-gray-300 prose-td:border prose-td:border-gray-300">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
          )}
          {streaming && <span className="inline-block w-1.5 h-4 bg-blue-500 animate-pulse ml-0.5" />}
          {!streaming && content && (
            <button
              onClick={(e) => { e.stopPropagation(); setShowRaw(!showRaw) }}
              className="mt-1 text-[10px] text-gray-400 hover:text-gray-600"
            >
              {showRaw ? 'rendered' : 'raw'}
            </button>
          )}
        </div>
        {!streaming && message.turnData && (
          <button
            className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-gray-600 text-xs self-start mt-1"
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
      <div className="text-center text-xs text-gray-400 py-1">{content}</div>
    )
  }

  return null
}
