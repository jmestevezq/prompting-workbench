import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { Agent, Transcript } from '../api/types'
import PromptEditor from '../components/PromptEditor'
import TranscriptPicker from '../components/TranscriptPicker'

interface GeneratedItem {
  content: string
  tags: string[]
  savedId: string | null
  saving: boolean
}

function TagEditor({ tags, onChange }: { tags: string[]; onChange: (tags: string[]) => void }) {
  const [input, setInput] = useState('')

  const addTag = () => {
    const tag = input.trim().toLowerCase()
    if (tag && !tags.includes(tag)) {
      onChange([...tags, tag])
    }
    setInput('')
  }

  const removeTag = (tag: string) => {
    onChange(tags.filter((t) => t !== tag))
  }

  return (
    <div className="flex flex-wrap items-center gap-1">
      {tags.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-0.5 text-xs bg-blue-50 text-blue-600 rounded px-1.5 py-0.5"
        >
          {tag}
          <button
            onClick={() => removeTag(tag)}
            className="text-blue-400 hover:text-blue-700 ml-0.5"
          >
            &times;
          </button>
        </span>
      ))}
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.preventDefault(); addTag() }
        }}
        placeholder="Add tag..."
        className="text-xs border border-gray-200 rounded px-1.5 py-0.5 w-20 focus:outline-none focus:border-blue-400"
      />
    </div>
  )
}

export default function Generator() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedRefIds, setSelectedRefIds] = useState<Set<string>>(new Set())
  const [selectedAgentId, setSelectedAgentId] = useState<string>('')
  const [prompt, setPrompt] = useState('Generate transcripts where the agent makes a math error when calculating totals.')
  const [count, setCount] = useState(5)
  const [model, setModel] = useState('gemini-2.5-pro')
  const [generating, setGenerating] = useState(false)
  const [items, setItems] = useState<GeneratedItem[]>([])

  useEffect(() => {
    api.listTranscripts().then(setTranscripts)
    api.listAgents().then(setAgents)
  }, [])

  const handleGenerate = async () => {
    if (!selectedRefIds.size) return
    setGenerating(true)
    setItems([])
    try {
      const result = await api.generateTranscripts({
        reference_transcript_ids: Array.from(selectedRefIds),
        prompt,
        count,
        model,
        agent_id: selectedAgentId || undefined,
        auto_save: false,
      })
      setItems(result.generated.map((g) => ({
        content: g.content,
        tags: g.tags,
        savedId: null,
        saving: false,
      })))
    } finally {
      setGenerating(false)
    }
  }

  const updateItem = useCallback((index: number, update: Partial<GeneratedItem>) => {
    setItems((prev) => prev.map((item, i) => i === index ? { ...item, ...update } : item))
  }, [])

  const handleSave = async (index: number) => {
    const item = items[index]
    if (item.savedId || item.saving) return
    updateItem(index, { saving: true })
    try {
      const saved = await api.createTranscript({
        name: `Generated #${index + 1}`,
        content: item.content,
        labels: {},
        source: 'generated',
        tags: item.tags,
      })
      updateItem(index, { savedId: saved.id, saving: false })
      api.listTranscripts().then(setTranscripts)
    } catch {
      updateItem(index, { saving: false })
    }
  }

  return (
    <div className="h-full grid grid-cols-2 gap-0">
      {/* Left: Config */}
      <div className="border-r border-gray-200 p-4 overflow-auto">
        <h2 className="text-lg font-semibold mb-4">Transcript Generator</h2>

        {/* Reference Transcripts */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Reference Transcripts
          </label>
          <TranscriptPicker
            transcripts={transcripts}
            selectedIds={selectedRefIds}
            onSelectionChange={setSelectedRefIds}
          />
        </div>

        {/* Agent Context (optional) */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Agent Context (optional)
          </label>
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            className="border border-gray-300 rounded px-2 py-1.5 text-sm w-full"
          >
            <option value="">None</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>{agent.name}</option>
            ))}
          </select>
          <p className="text-xs text-gray-400 mt-1">
            Include agent's system prompt and tools as context for generation
          </p>
        </div>

        {/* Generation Prompt */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Generation Prompt</label>
          <PromptEditor value={prompt} onChange={setPrompt} height="150px" />
        </div>

        {/* Count & Model */}
        <div className="flex gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Count</label>
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              min={1}
              max={20}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm w-20"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-2.0-flash">gemini-2.0-flash</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating || !selectedRefIds.size}
          className="bg-blue-600 text-white px-6 py-2 rounded text-sm font-medium disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate Transcripts'}
        </button>
      </div>

      {/* Right: Results */}
      <div className="p-4 overflow-auto bg-gray-50">
        <h3 className="text-sm font-medium mb-3">
          Generated Results {items.length > 0 && `(${items.length})`}
        </h3>
        {!items.length && (
          <div className="text-center text-gray-400 text-sm mt-16">
            Generated transcripts will appear here
          </div>
        )}
        <div className="space-y-3">
          {items.map((item, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-3 flex flex-col">
              <div className="mb-2">
                <span className="text-xs font-medium text-gray-600">Transcript #{i + 1}</span>
              </div>
              <pre
                className="text-xs bg-gray-50 rounded p-2 whitespace-pre-wrap overflow-auto resize-y"
                style={{ minHeight: '6rem', height: '12rem' }}
              >
                {item.content}
              </pre>
              <div className="flex items-center justify-between mt-2 gap-2">
                <TagEditor
                  tags={item.tags}
                  onChange={(tags) => updateItem(i, { tags })}
                />
                {item.savedId ? (
                  <span className="text-xs text-green-600 whitespace-nowrap">
                    Saved: {item.savedId.slice(0, 8)}...
                  </span>
                ) : (
                  <button
                    onClick={() => handleSave(i)}
                    disabled={item.saving}
                    className="text-xs bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700 disabled:opacity-50 whitespace-nowrap"
                  >
                    {item.saving ? 'Saving...' : 'Save'}
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
