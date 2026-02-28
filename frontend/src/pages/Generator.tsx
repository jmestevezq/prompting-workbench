import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Transcript } from '../api/types'
import PromptEditor from '../components/PromptEditor'

export default function Generator() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [selectedRefIds, setSelectedRefIds] = useState<string[]>([])
  const [prompt, setPrompt] = useState('Generate 5 transcripts where the agent makes a math error when calculating totals.')
  const [count, setCount] = useState(5)
  const [model, setModel] = useState('gemini-2.5-pro')
  const [generating, setGenerating] = useState(false)
  const [generated, setGenerated] = useState<{ content: string; tags: string[] }[]>([])
  const [savedIds, setSavedIds] = useState<string[]>([])

  useEffect(() => {
    api.listTranscripts().then(setTranscripts)
  }, [])

  const toggleRef = (id: string) => {
    setSelectedRefIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const handleGenerate = async () => {
    if (!selectedRefIds.length) return
    setGenerating(true)
    setGenerated([])
    try {
      const result = await api.generateTranscripts({
        reference_transcript_ids: selectedRefIds,
        prompt,
        count,
        model,
      })
      setGenerated(result.generated)
      setSavedIds(result.saved_ids)
      // Refresh transcript list
      api.listTranscripts().then(setTranscripts)
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="h-full grid grid-cols-2 gap-0">
      {/* Left: Config */}
      <div className="border-r border-gray-200 p-4 overflow-auto">
        <h2 className="text-lg font-semibold mb-4">Transcript Generator</h2>

        {/* Reference Transcripts */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Reference Transcripts ({selectedRefIds.length} selected)
          </label>
          <div className="max-h-48 overflow-auto border border-gray-200 rounded">
            {transcripts.map((t) => (
              <label
                key={t.id}
                className={`flex items-center gap-2 px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 ${
                  selectedRefIds.includes(t.id) ? 'bg-blue-50' : ''
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedRefIds.includes(t.id)}
                  onChange={() => toggleRef(t.id)}
                />
                {t.name || t.id.slice(0, 8)}
                <span className="text-xs text-gray-400 ml-auto">{t.source}</span>
              </label>
            ))}
            {!transcripts.length && (
              <div className="text-sm text-gray-400 p-3">No transcripts yet. Import some first.</div>
            )}
          </div>
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
          disabled={generating || !selectedRefIds.length}
          className="bg-blue-600 text-white px-6 py-2 rounded text-sm font-medium disabled:opacity-50"
        >
          {generating ? 'Generating...' : 'Generate Transcripts'}
        </button>
      </div>

      {/* Right: Results */}
      <div className="p-4 overflow-auto bg-gray-50">
        <h3 className="text-sm font-medium mb-3">
          Generated Results {generated.length > 0 && `(${generated.length})`}
        </h3>
        {!generated.length && (
          <div className="text-center text-gray-400 text-sm mt-16">
            Generated transcripts will appear here
          </div>
        )}
        <div className="space-y-3">
          {generated.map((g, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-600">Transcript #{i + 1}</span>
                <div className="flex gap-1">
                  {g.tags.map((tag) => (
                    <span key={tag} className="text-xs bg-blue-50 text-blue-600 rounded px-1">{tag}</span>
                  ))}
                </div>
              </div>
              <pre className="text-xs bg-gray-50 rounded p-2 whitespace-pre-wrap max-h-48 overflow-auto">
                {g.content}
              </pre>
              {savedIds[i] && (
                <div className="text-xs text-green-600 mt-1">Saved: {savedIds[i].slice(0, 8)}...</div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
