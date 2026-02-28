import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Transcript, Autorater as AutoraterType, EvalRun, EvalResult } from '../api/types'
import DataTable from '../components/DataTable'
import MetricsCard from '../components/MetricsCard'
import StatusBadge from '../components/StatusBadge'
import PromptEditor from '../components/PromptEditor'
import JsonEditor from '../components/JsonEditor'

type Tab = 'transcripts' | 'autoraters' | 'eval-runs'

export default function Autorater() {
  const [activeTab, setActiveTab] = useState<Tab>('transcripts')

  return (
    <div className="h-full flex flex-col">
      <div className="flex border-b border-gray-200 bg-white px-4 shrink-0">
        {(['transcripts', 'autoraters', 'eval-runs'] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab === 'transcripts' ? 'Transcripts' : tab === 'autoraters' ? 'Autoraters' : 'Eval Runs'}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {activeTab === 'transcripts' && <TranscriptsTab />}
        {activeTab === 'autoraters' && <AutoratersTab />}
        {activeTab === 'eval-runs' && <EvalRunsTab />}
      </div>
    </div>
  )
}

// --- Transcripts Tab ---
function TranscriptsTab() {
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [selected, setSelected] = useState<Transcript | null>(null)
  const [tagFilter, setTagFilter] = useState('')
  const [showImport, setShowImport] = useState(false)
  const [importJson, setImportJson] = useState('')

  useEffect(() => {
    api.listTranscripts(tagFilter || undefined).then(setTranscripts)
  }, [tagFilter])

  const handleImport = async () => {
    try {
      const data = JSON.parse(importJson)
      const items = Array.isArray(data) ? data : [data]
      await api.importTranscripts(items)
      setShowImport(false)
      setImportJson('')
      api.listTranscripts().then(setTranscripts)
    } catch {
      // Invalid JSON
    }
  }

  const handleUpdateLabels = async (id: string, labels: Record<string, string>) => {
    await api.updateTranscript(id, { labels })
    setTranscripts((prev) => prev.map((t) => (t.id === id ? { ...t, labels } : t)))
    if (selected?.id === id) setSelected({ ...selected, labels })
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 p-4 overflow-auto">
        <div className="flex items-center gap-2 mb-3">
          <input
            value={tagFilter}
            onChange={(e) => setTagFilter(e.target.value)}
            placeholder="Filter by tag..."
            className="border border-gray-300 rounded px-2 py-1 text-sm flex-1"
          />
          <button
            onClick={() => setShowImport(!showImport)}
            className="bg-blue-600 text-white px-3 py-1 rounded text-sm"
          >
            Import
          </button>
        </div>

        {showImport && (
          <div className="mb-4 border border-gray-200 rounded p-3">
            <label className="text-xs font-medium text-gray-500 mb-1 block">Paste JSON/JSONL</label>
            <JsonEditor value={importJson} onChange={setImportJson} height="150px" />
            <button onClick={handleImport} className="mt-2 bg-blue-600 text-white px-3 py-1 rounded text-xs">
              Import Transcripts
            </button>
          </div>
        )}

        <DataTable
          columns={[
            { key: 'name', header: 'Name', sortable: true },
            { key: 'source', header: 'Source', render: (r) => <StatusBadge status={(r as Transcript).source} /> },
            { key: 'labels', header: 'Labels', render: (r) => {
              const t = r as Transcript
              return Object.entries(t.labels).map(([k, v]) => (
                <span key={k} className="inline-block mr-1 text-xs bg-gray-100 rounded px-1">{k}: {v}</span>
              ))
            }},
            { key: 'tags', header: 'Tags', render: (r) => {
              const t = r as Transcript
              return (t.tags ?? []).map((tag) => (
                <span key={tag} className="inline-block mr-1 text-xs bg-blue-50 text-blue-600 rounded px-1">{tag}</span>
              ))
            }},
            { key: 'created_at', header: 'Created', sortable: true },
          ]}
          data={transcripts}
          onRowClick={(row) => setSelected(row as Transcript)}
        />
      </div>

      {selected && (
        <div className="w-96 border-l border-gray-200 p-4 overflow-auto bg-gray-50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-medium text-sm">{selected.name || 'Transcript'}</h3>
            <button onClick={() => setSelected(null)} className="text-gray-400 hover:text-gray-600 text-xs">Close</button>
          </div>
          <pre className="text-xs bg-white rounded p-3 mb-3 whitespace-pre-wrap max-h-48 overflow-auto border">
            {selected.content}
          </pre>
          <div className="mb-3">
            <label className="text-xs font-medium text-gray-500 block mb-1">Labels</label>
            {Object.entries(selected.labels).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2 mb-1">
                <span className="text-xs text-gray-600 w-24">{key}</span>
                <select
                  value={value}
                  onChange={(e) => handleUpdateLabels(selected.id, { ...selected.labels, [key]: e.target.value })}
                  className="text-xs border rounded px-1 py-0.5"
                >
                  <option value="pass">pass</option>
                  <option value="fail">fail</option>
                </select>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// --- Autoraters Tab ---
function AutoratersTab() {
  const [autoraters, setAutoraters] = useState<AutoraterType[]>([])
  const [selected, setSelected] = useState<AutoraterType | null>(null)
  const [editName, setEditName] = useState('')
  const [editPrompt, setEditPrompt] = useState('')
  const [editModel, setEditModel] = useState('gemini-2.5-pro')

  useEffect(() => {
    api.listAutoraters().then(setAutoraters)
  }, [])

  const selectAutorater = (a: AutoraterType) => {
    setSelected(a)
    setEditName(a.name)
    setEditPrompt(a.prompt)
    setEditModel(a.model)
  }

  const handleSave = async () => {
    if (selected) {
      const updated = await api.updateAutorater(selected.id, {
        name: editName,
        prompt: editPrompt,
        model: editModel,
      })
      setAutoraters((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
      setSelected(updated)
    }
  }

  const handleCreate = async () => {
    const created = await api.createAutorater({
      name: 'New Autorater',
      prompt: 'Evaluate the following transcript:\n\n{{transcript}}\n\nRespond with JSON: {"assessment": "pass|fail", "explanation": "..."}',
    })
    setAutoraters((prev) => [created, ...prev])
    selectAutorater(created)
  }

  return (
    <div className="flex h-full">
      <div className="w-64 border-r border-gray-200 p-3 overflow-auto">
        <button onClick={handleCreate} className="w-full bg-blue-600 text-white px-3 py-1.5 rounded text-sm mb-3">
          New Autorater
        </button>
        <div className="space-y-1">
          {autoraters.map((a) => (
            <div
              key={a.id}
              onClick={() => selectAutorater(a)}
              className={`px-3 py-2 rounded text-sm cursor-pointer ${selected?.id === a.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50'}`}
            >
              {a.name}
            </div>
          ))}
        </div>
      </div>

      {selected ? (
        <div className="flex-1 p-4 overflow-auto">
          <div className="space-y-4 max-w-3xl">
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Name</label>
              <input
                value={editName}
                onChange={(e) => setEditName(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Model</label>
              <select value={editModel} onChange={(e) => setEditModel(e.target.value)} className="border border-gray-300 rounded px-3 py-1.5 text-sm">
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500 mb-1 block">Prompt (use {'{{transcript}}'} placeholder)</label>
              <PromptEditor value={editPrompt} onChange={setEditPrompt} height="300px" />
            </div>
            <button onClick={handleSave} className="bg-blue-600 text-white px-4 py-2 rounded text-sm">
              Save
            </button>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-gray-400 text-sm">Select or create an autorater</div>
      )}
    </div>
  )
}

// --- Eval Runs Tab ---
function EvalRunsTab() {
  const [autoraters, setAutoraters] = useState<AutoraterType[]>([])
  const [transcripts, setTranscripts] = useState<Transcript[]>([])
  const [runs, setRuns] = useState<EvalRun[]>([])
  const [selectedRun, setSelectedRun] = useState<EvalRun | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [selectedAutoraterId, setSelectedAutoraterId] = useState('')
  const [launching, setLaunching] = useState(false)

  useEffect(() => {
    api.listAutoraters().then(setAutoraters)
    api.listTranscripts().then(setTranscripts)
    api.listEvalRuns().then(setRuns)
  }, [])

  const handleLaunch = async () => {
    if (!selectedAutoraterId || !transcripts.length) return
    setLaunching(true)
    try {
      const run = await api.startEvalRun(selectedAutoraterId, transcripts.map((t) => t.id))
      setRuns((prev) => [run, ...prev])
    } finally {
      setLaunching(false)
    }
  }

  const handleSelectRun = async (run: EvalRun) => {
    // Refresh to get latest status
    const latest = await api.getEvalRun(run.id)
    setSelectedRun(latest)
    const res = await api.getEvalResults(run.id)
    setResults(res)
  }

  return (
    <div className="p-4">
      {/* Launch Section */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium mb-3">Launch Eval Run</h3>
        <div className="flex items-end gap-3">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Autorater</label>
            <select
              value={selectedAutoraterId}
              onChange={(e) => setSelectedAutoraterId(e.target.value)}
              className="border border-gray-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="">Select...</option>
              {autoraters.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select>
          </div>
          <div className="text-xs text-gray-500">{transcripts.length} transcripts</div>
          <button
            onClick={handleLaunch}
            disabled={launching || !selectedAutoraterId}
            className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
          >
            {launching ? 'Launching...' : 'Run Evaluation'}
          </button>
        </div>
      </div>

      {/* Run History */}
      <div className="grid grid-cols-[1fr_1fr] gap-4">
        <div>
          <h3 className="text-sm font-medium mb-2">Run History</h3>
          <DataTable
            columns={[
              { key: 'created_at', header: 'Date', sortable: true },
              { key: 'status', header: 'Status', render: (r) => <StatusBadge status={(r as EvalRun).status} /> },
              { key: 'metrics', header: 'Accuracy', render: (r) => {
                const run = r as EvalRun
                return run.metrics?.accuracy != null ? `${(run.metrics.accuracy * 100).toFixed(1)}%` : '-'
              }},
            ]}
            data={runs}
            onRowClick={(row) => handleSelectRun(row as EvalRun)}
          />
        </div>

        {selectedRun && (
          <div>
            <h3 className="text-sm font-medium mb-2">Run Detail</h3>
            <div className="flex items-center gap-2 mb-3">
              <StatusBadge status={selectedRun.status} />
              <span className="text-xs text-gray-500">{selectedRun.created_at}</span>
            </div>
            {selectedRun.metrics && (
              <MetricsCard
                title="Overall Metrics"
                metrics={{
                  accuracy: selectedRun.metrics.accuracy,
                  total: selectedRun.metrics.total,
                  correct: selectedRun.metrics.correct,
                }}
              />
            )}
            <div className="mt-3">
              <h4 className="text-xs font-medium text-gray-500 mb-2">Per-Transcript Results</h4>
              <div className="space-y-1 max-h-96 overflow-auto">
                {results.map((r) => (
                  <details key={r.id} className="border border-gray-200 rounded text-xs">
                    <summary className={`px-3 py-1.5 cursor-pointer ${r.match ? 'bg-green-50' : 'bg-red-50'}`}>
                      {r.transcript_id.slice(0, 8)}... — {r.match ? 'Match' : 'Mismatch'}
                    </summary>
                    <div className="px-3 py-2 space-y-1">
                      <div><span className="text-gray-500">Predicted:</span> {JSON.stringify(r.predicted_labels)}</div>
                      <div><span className="text-gray-500">Expected:</span> {JSON.stringify(r.ground_truth_labels)}</div>
                    </div>
                  </details>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
