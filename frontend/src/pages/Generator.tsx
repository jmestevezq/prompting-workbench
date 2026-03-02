import { useState, useEffect, useCallback, useMemo } from 'react'
import { api } from '../api/client'
import type { Agent, Transcript } from '../api/types'
import PromptEditor from '../components/PromptEditor'
import TranscriptPicker from '../components/TranscriptPicker'
import TagEditor from '../components/TagEditor'

interface GeneratedItem {
  name: string
  content: string
  tags: string[]
  savedId: string | null
  saving: boolean
}

function formatTimestamp() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(d.getHours())}${pad(d.getMinutes())}`
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

  // Collect all known tags for autocomplete
  const allTags = useMemo(() => {
    const tagSet = new Set<string>()
    for (const t of transcripts) {
      if (t.tags) t.tags.forEach((tag) => tagSet.add(tag))
    }
    for (const item of items) {
      item.tags.forEach((tag) => tagSet.add(tag))
    }
    return Array.from(tagSet).sort()
  }, [transcripts, items])

  useEffect(() => {
    api.listTranscripts().then(setTranscripts)
    api.listAgents().then(setAgents)
  }, [])

  const handleGenerate = async () => {
    setGenerating(true)
    setItems([])
    const ts = formatTimestamp()
    try {
      const result = await api.generateTranscripts({
        reference_transcript_ids: Array.from(selectedRefIds),
        prompt,
        count,
        model,
        agent_id: selectedAgentId || undefined,
        auto_save: false,
      })
      setItems(result.generated.map((g, i) => ({
        name: `transcript-${i + 1}-${ts}`,
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
        name: item.name,
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
      <div className="border-r border-slate-200 p-4 overflow-auto">
        <h2 className="text-lg font-semibold mb-4">Transcript Generator</h2>

        {/* Reference Transcripts */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Reference Transcripts (optional)
          </label>
          <TranscriptPicker
            transcripts={transcripts}
            selectedIds={selectedRefIds}
            onSelectionChange={setSelectedRefIds}
          />
        </div>

        {/* Agent Context (optional) */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Agent Context (optional)
          </label>
          <select
            value={selectedAgentId}
            onChange={(e) => setSelectedAgentId(e.target.value)}
            className="border border-slate-300 rounded px-2 py-1.5 text-sm w-full"
          >
            <option value="">None</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>{agent.name}</option>
            ))}
          </select>
          <p className="text-xs text-slate-400 mt-1">
            Include agent's system prompt and tools as context for generation
          </p>
        </div>

        {/* Generation Prompt */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-slate-700 mb-1">Generation Prompt</label>
          <PromptEditor value={prompt} onChange={setPrompt} height="150px" />
        </div>

        {/* Count & Model */}
        <div className="flex gap-4 mb-4">
          <div>
            <label className="block text-xs text-slate-500 mb-1">Count</label>
            <input
              type="number"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              min={1}
              max={20}
              className="border border-slate-300 rounded px-2 py-1.5 text-sm w-20"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-500 mb-1">Model</label>
            <select
              value={model}
              onChange={(e) => setModel(e.target.value)}
              className="border border-slate-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-2.0-flash">gemini-2.0-flash</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={generating}
          className="bg-indigo-600 text-white px-6 py-2 rounded text-sm font-medium disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate Transcripts'}
        </button>
      </div>

      {/* Right: Results */}
      <div className="p-4 overflow-auto bg-slate-50">
        <h3 className="text-sm font-medium mb-3">
          Generated Results {items.length > 0 && `(${items.length})`}
        </h3>
        {!items.length && (
          <div className="text-center text-slate-400 text-sm mt-16">
            Generated transcripts will appear here
          </div>
        )}
        <div className="space-y-3">
          {items.map((item, i) => (
            <div key={i} className="bg-white border border-slate-200 rounded-lg p-3 flex flex-col gap-2">
              {/* Name */}
              <input
                value={item.name}
                onChange={(e) => updateItem(i, { name: e.target.value })}
                disabled={!!item.savedId}
                className="text-sm font-medium text-slate-800 border border-slate-200 rounded px-2 py-1 focus:outline-none focus:border-indigo-400 disabled:bg-slate-50 disabled:text-slate-500"
              />

              {/* Content */}
              <pre
                className="text-xs bg-slate-50 rounded p-2 whitespace-pre-wrap overflow-auto resize-y"
                style={{ minHeight: '6rem', height: '12rem' }}
              >
                {item.content}
              </pre>

              {/* Tags + Save */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <TagEditor
                    tags={item.tags}
                    onChange={(tags) => updateItem(i, { tags })}
                    suggestions={allTags}
                  />
                </div>
                <div className="flex-shrink-0">
                  {item.savedId ? (
                    <span className="text-xs text-emerald-600 whitespace-nowrap leading-6">
                      Saved {item.savedId.slice(0, 8)}
                    </span>
                  ) : (
                    <button
                      onClick={() => handleSave(i)}
                      disabled={item.saving}
                      className="text-xs bg-emerald-600 text-white px-3 py-1 rounded hover:bg-emerald-700 disabled:opacity-50 whitespace-nowrap"
                    >
                      {item.saving ? 'Saving...' : 'Save'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
