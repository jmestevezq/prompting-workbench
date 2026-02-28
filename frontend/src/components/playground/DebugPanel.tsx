import { useState } from 'react'
import type { Turn } from '../../api/types'
import JsonEditor from '../JsonEditor'

interface DebugPanelProps {
  selectedTurn: Turn | null
  onRerun: (turnId: string, overrides: Record<string, unknown>) => void
}

type Tab = 'prompt' | 'tools' | 'request' | 'response' | 'tokens'

export default function DebugPanel({ selectedTurn, onRerun }: DebugPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>('prompt')
  const [editMode, setEditMode] = useState(false)
  const [editedPrompt, setEditedPrompt] = useState('')

  const tabs: { key: Tab; label: string }[] = [
    { key: 'prompt', label: 'Prompt' },
    { key: 'tools', label: 'Tool Calls' },
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
    onRerun(selectedTurn.id, overrides)
    setEditMode(false)
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
            className={`px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
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
        {activeTab === 'tools' && <ToolsTab turn={selectedTurn} />}
        {activeTab === 'request' && <RawTab data={selectedTurn.raw_request} />}
        {activeTab === 'response' && <RawTab data={selectedTurn.raw_response} />}
        {activeTab === 'tokens' && <TokensTab turn={selectedTurn} />}
      </div>

      {/* Rerun controls */}
      <div className="p-3 border-t border-gray-200 shrink-0 flex gap-2">
        <button
          onClick={() => setEditMode(!editMode)}
          className="text-xs px-3 py-1.5 rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
        >
          {editMode ? 'Cancel Edit' : 'Edit & Rerun'}
        </button>
        {editMode && (
          <button
            onClick={handleRerun}
            className="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            Rerun
          </button>
        )}
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
        />
      </div>
    )
  }

  return (
    <div>
      <label className="text-xs font-medium text-gray-500 mb-1 block">System Prompt</label>
      <pre className="text-xs bg-gray-50 rounded p-3 whitespace-pre-wrap max-h-96 overflow-auto">
        {systemPrompt || 'N/A'}
      </pre>
    </div>
  )
}

function ToolsTab({ turn }: { turn: Turn }) {
  const calls = (turn.tool_calls ?? []) as Array<{ name: string; args: unknown }>
  const responses = (turn.tool_responses ?? []) as Array<{ name: string; response: unknown }>

  if (!calls.length) {
    return <div className="text-xs text-gray-400">No tool calls in this turn</div>
  }

  return (
    <div className="space-y-3">
      {calls.map((call, i) => (
        <div key={i} className="border border-gray-200 rounded overflow-hidden">
          <div className="bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700">
            {call.name}
          </div>
          <pre className="px-3 py-2 text-xs bg-white overflow-auto max-h-32">
            {JSON.stringify(call.args, null, 2)}
          </pre>
          {responses[i] && (
            <>
              <div className="bg-emerald-50 px-3 py-1.5 text-xs font-medium text-emerald-700 border-t border-gray-200">
                Response
              </div>
              <pre className="px-3 py-2 text-xs bg-white overflow-auto max-h-32">
                {JSON.stringify(responses[i].response, null, 2)}
              </pre>
            </>
          )}
        </div>
      ))}
    </div>
  )
}

function RawTab({ data }: { data: unknown }) {
  return (
    <pre className="text-xs bg-gray-50 rounded p-3 whitespace-pre-wrap overflow-auto max-h-[calc(100vh-250px)]">
      {data ? JSON.stringify(data, null, 2) : 'N/A'}
    </pre>
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
