import { useState, useEffect, useCallback } from 'react'
import type { Turn } from '../../api/types'
import JsonEditor from '../JsonEditor'

function CopyButton({ text, label = 'Copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation()
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }, [text])

  return (
    <button
      onClick={handleCopy}
      className="text-[10px] px-1.5 py-0.5 rounded border border-gray-200 text-gray-400 hover:text-gray-600 hover:border-gray-300 hover:bg-gray-50 transition-colors shrink-0"
      title={label}
    >
      {copied ? 'Copied!' : label}
    </button>
  )
}

interface DebugPanelProps {
  selectedTurn: Turn | null
  onRerun: (turnId: string, overrides: Record<string, unknown>) => void
  isStreaming?: boolean
}

type Tab = 'prompt' | 'tools' | 'request' | 'response' | 'tokens'

export default function DebugPanel({ selectedTurn, onRerun, isStreaming }: DebugPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('prompt')
  const [editMode, setEditMode] = useState(false)
  const [editedPrompt, setEditedPrompt] = useState('')
  const [editedToolResponses, setEditedToolResponses] = useState<Record<string, string>>({})

  // Reset edit state when selected turn changes
  useEffect(() => {
    setEditMode(false)
    setEditedPrompt('')
    setEditedToolResponses({})
  }, [selectedTurn?.id])

  const hasPromptEdit = editedPrompt !== ''
  const hasToolEdits = Object.keys(editedToolResponses).length > 0
  const hasAnyEdits = hasPromptEdit || hasToolEdits

  const tabs: { key: Tab; label: string; hasEdit?: boolean }[] = [
    { key: 'prompt', label: 'Prompt', hasEdit: hasPromptEdit },
    { key: 'tools', label: 'Tool Calls', hasEdit: hasToolEdits },
    { key: 'request', label: 'Raw Req' },
    { key: 'response', label: 'Raw Resp' },
    { key: 'tokens', label: 'Tokens' },
  ]

  const handleRerun = () => {
    if (!selectedTurn) return
    const overrides: Record<string, unknown> = {}
    if (editedPrompt) {
      overrides.system_prompt = editedPrompt
    }
    // Collect edited tool responses
    const parsedResponses: Record<string, unknown> = {}
    let hasEditedResponses = false
    for (const [key, val] of Object.entries(editedToolResponses)) {
      try {
        parsedResponses[key] = JSON.parse(val)
        hasEditedResponses = true
      } catch {
        // skip invalid JSON
      }
    }
    if (hasEditedResponses) {
      overrides.tool_responses = parsedResponses
    }
    onRerun(selectedTurn.id, overrides)
    setEditMode(false)
    setEditedPrompt('')
    setEditedToolResponses({})
  }

  const handleCancelEdit = () => {
    setEditMode(false)
    setEditedPrompt('')
    setEditedToolResponses({})
  }

  if (!selectedTurn) {
    return (
      <div className="bg-gray-50 flex items-center justify-center text-gray-400 text-sm">
        Click an agent message to inspect
      </div>
    )
  }

  return (
    <div className="bg-white flex flex-col overflow-hidden">
      {/* Tabs */}
      <div className="flex border-b border-gray-200 shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`relative px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
            {editMode && tab.hasEdit && (
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-amber-400 rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {activeTab === 'prompt' && (
          <PromptTab
            turn={selectedTurn}
            editMode={editMode}
            editedPrompt={editedPrompt}
            onEditPrompt={setEditedPrompt}
          />
        )}
        {activeTab === 'tools' && (
          <ToolsTab
            turn={selectedTurn}
            editMode={editMode}
            editedResponses={editedToolResponses}
            onEditResponse={(name, val) =>
              setEditedToolResponses((prev) => ({ ...prev, [name]: val }))
            }
          />
        )}
        {activeTab === 'request' && <RawTab data={selectedTurn.raw_request} />}
        {activeTab === 'response' && <RawTab data={selectedTurn.raw_response} />}
        {activeTab === 'tokens' && <TokensTab turn={selectedTurn} />}
      </div>

      {/* Controls */}
      <div className="p-3 border-t border-gray-200 shrink-0 flex items-center gap-2">
        <button
          onClick={() => editMode ? handleCancelEdit() : setEditMode(true)}
          className={`text-xs px-3 py-1.5 rounded border transition-colors ${
            editMode
              ? 'border-amber-300 bg-amber-50 text-amber-700 hover:bg-amber-100'
              : 'border-gray-300 text-gray-700 hover:bg-gray-50'
          }`}
        >
          {editMode ? 'Cancel' : 'Edit'}
        </button>
        <button
          onClick={handleRerun}
          disabled={isStreaming || (!editMode && !hasAnyEdits)}
          className={`text-xs px-3 py-1.5 rounded transition-colors flex items-center gap-1.5 ${
            isStreaming
              ? 'bg-blue-500 text-white cursor-wait'
              : editMode || hasAnyEdits
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isStreaming && (
            <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
          {isStreaming ? 'Generating...' : `Rerun${hasAnyEdits ? ' with edits' : ''}`}
        </button>
      </div>
    </div>
  )
}

function PromptTab({
  turn,
  editMode,
  editedPrompt,
  onEditPrompt,
}: {
  turn: Turn
  editMode: boolean
  editedPrompt: string
  onEditPrompt: (val: string) => void
}) {
  // Extract system prompt from raw request
  const rawReq = turn.raw_request as unknown
  let systemPrompt = ''
  if (Array.isArray(rawReq) && rawReq.length > 0) {
    systemPrompt = (rawReq[0] as Record<string, string>)?.system_instruction ?? ''
  } else if (rawReq && typeof rawReq === 'object') {
    systemPrompt = (rawReq as Record<string, string>).system_instruction ?? ''
  }

  if (editMode) {
    return (
      <div>
        <label className="text-xs font-medium text-gray-500 mb-1 block">Edit System Prompt</label>
        <JsonEditor
          value={editedPrompt || systemPrompt}
          onChange={onEditPrompt}
          height="250px"
          language="text"
        />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-gray-500">System Prompt</label>
        {systemPrompt && <CopyButton text={systemPrompt} />}
      </div>
      <pre className="text-xs bg-gray-50 rounded p-3 whitespace-pre-wrap max-h-96 overflow-auto">
        {systemPrompt || 'N/A'}
      </pre>
    </div>
  )
}

function ToolsTab({
  turn,
  editMode,
  editedResponses,
  onEditResponse,
}: {
  turn: Turn
  editMode: boolean
  editedResponses: Record<string, string>
  onEditResponse: (name: string, val: string) => void
}) {
  const calls = (turn.tool_calls ?? []) as Array<{ name: string; args: unknown }>
  const responses = (turn.tool_responses ?? []) as Array<{ name: string; response: unknown }>

  if (!calls.length) {
    return <div className="text-xs text-gray-400">No tool calls in this turn</div>
  }

  return (
    <div className="space-y-3">
      {calls.map((call, i) => {
        const resp = responses[i]
        const responseJson = resp ? JSON.stringify(resp.response, null, 2) : ''
        const editKey = call.name

        return (
          <div key={i} className="border border-gray-200 rounded overflow-hidden">
            <div className="bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 flex items-center justify-between">
              <span>{call.name}</span>
              <CopyButton text={JSON.stringify(call.args, null, 2)} label="Copy args" />
            </div>
            <pre className="px-3 py-2 text-xs bg-white overflow-auto max-h-32">
              {JSON.stringify(call.args, null, 2)}
            </pre>
            {resp && (
              <>
                <div className="bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 border-t border-gray-200 flex items-center justify-between">
                  <span>Response</span>
                  <div className="flex items-center gap-2">
                    {editMode && (
                      <span className="text-emerald-500 text-[10px] font-normal">editable</span>
                    )}
                    <CopyButton text={responseJson} label="Copy" />
                  </div>
                </div>
                {editMode ? (
                  <div className="border-t border-gray-200">
                    <JsonEditor
                      value={editedResponses[editKey] ?? responseJson}
                      onChange={(val) => onEditResponse(editKey, val)}
                      height="120px"
                    />
                  </div>
                ) : (
                  <pre className="px-3 py-2 text-xs bg-white overflow-auto max-h-32">
                    {responseJson}
                  </pre>
                )}
              </>
            )}
          </div>
        )
      })}
    </div>
  )
}

function RawTab({ data }: { data: unknown }) {
  const formatted = data ? JSON.stringify(data, null, 2) : ''
  return (
    <div>
      {formatted && (
        <div className="flex justify-end mb-1">
          <CopyButton text={formatted} />
        </div>
      )}
      <pre className="text-xs bg-gray-50 rounded p-3 whitespace-pre-wrap overflow-auto max-h-[calc(100vh-250px)]">
        {formatted || 'N/A'}
      </pre>
    </div>
  )
}

function TokensTab({ turn }: { turn: Turn }) {
  const usage = turn.token_usage
  if (!usage) {
    return <div className="text-xs text-gray-400">No token data</div>
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-50 rounded p-3">
          <div className="text-xs text-gray-500">Prompt Tokens</div>
          <div className="text-lg font-semibold">{usage.prompt_tokens ?? 0}</div>
        </div>
        <div className="bg-gray-50 rounded p-3">
          <div className="text-xs text-gray-500">Completion Tokens</div>
          <div className="text-lg font-semibold">{usage.completion_tokens ?? 0}</div>
        </div>
        <div className="bg-blue-50 rounded p-3 col-span-2">
          <div className="text-xs text-blue-500">Total Tokens</div>
          <div className="text-lg font-semibold text-blue-700">{usage.total ?? 0}</div>
        </div>
      </div>
    </div>
  )
}
