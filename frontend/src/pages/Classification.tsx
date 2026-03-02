import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { api } from '../api/client'
import type {
  GoldenTransaction, ClassificationPrompt, ClassificationRun, ClassificationResult,
} from '../api/types'
import DataTable from '../components/DataTable'
import MetricsCard from '../components/MetricsCard'
import StatusBadge from '../components/StatusBadge'
import PromptEditor from '../components/PromptEditor'
import JsonEditor from '../components/JsonEditor'
import SubNav from '../components/SubNav'
import { useToast } from '../components/ToastProvider'
import { Database, FileCode2, Play } from 'lucide-react'

type Tab = 'golden-sets' | 'prompts' | 'eval-runs'

const subNavItems = [
  { key: 'golden-sets', label: 'Golden Sets', icon: Database },
  { key: 'prompts', label: 'Prompts', icon: FileCode2 },
  { key: 'eval-runs', label: 'Eval Runs', icon: Play },
]

export default function Classification() {
  const [activeTab, setActiveTab] = useState<Tab>('golden-sets')

  return (
    <div className="h-full flex flex-row">
      <SubNav items={subNavItems} active={activeTab} onChange={(key) => setActiveTab(key as Tab)} />
      <div className="flex-1 overflow-auto">
        {activeTab === 'golden-sets' && <GoldenSetsTab />}
        {activeTab === 'prompts' && <PromptsTab />}
        {activeTab === 'eval-runs' && <ClassificationRunsTab />}
      </div>
    </div>
  )
}

// --- Golden Sets Tab ---
function GoldenSetsTab() {
  const [items, setItems] = useState<GoldenTransaction[]>([])
  const [selected, setSelected] = useState<GoldenTransaction | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [importJson, setImportJson] = useState('')

  useEffect(() => {
    api.listGoldenSets().then(setItems)
  }, [])

  const handleImport = async () => {
    try {
      const data = JSON.parse(importJson)
      const arr = Array.isArray(data) ? data : [data]
      await api.importGoldenSets(arr)
      setShowImport(false)
      setImportJson('')
      api.listGoldenSets().then(setItems)
    } catch {
      // Invalid JSON
    }
  }

  const handleCreate = async () => {
    const created = await api.createGoldenSet({
      set_name: 'default',
      input_transactions: [],
      expected_output: [],
    })
    setItems((prev) => [created, ...prev])
    setSelected(created)
  }

  return (
    <div className="flex h-full">
      <div className="flex-1 p-4 overflow-auto">
        <div className="flex items-center gap-2 mb-3">
          <button onClick={handleCreate} className="bg-indigo-600 text-white px-3 py-1 rounded text-sm">New Entry</button>
          <button onClick={() => setShowImport(!showImport)} className="bg-slate-100 text-slate-700 px-3 py-1 rounded text-sm">Import</button>
        </div>

        {showImport && (
          <div className="mb-4 border border-slate-200 rounded p-3">
            <JsonEditor value={importJson} onChange={setImportJson} height="150px" />
            <button onClick={handleImport} className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded text-xs">Import</button>
          </div>
        )}

        <DataTable
          columns={[
            { key: 'set_name', header: 'Set', sortable: true },
            { key: 'input_transactions', header: 'Inputs', render: (r) => {
              const g = r as GoldenTransaction
              const arr = g.input_transactions as unknown[]
              return `${Array.isArray(arr) ? arr.length : 0} transactions`
            }},
            { key: 'tags', header: 'Tags', render: (r) => {
              const g = r as GoldenTransaction
              return (g.tags ?? []).map((tag) => (
                <span key={tag} className="inline-block mr-1 text-xs bg-indigo-50 text-indigo-600 rounded px-1">{tag}</span>
              ))
            }},
            { key: 'created_at', header: 'Created', sortable: true },
          ]}
          data={items}
          onRowClick={(row) => setSelected(row as GoldenTransaction)}
        />
      </div>

      {selected && (
        <div className="w-[420px] border-l border-slate-200 p-4 overflow-auto bg-slate-50">
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-medium text-sm">Golden Entry: {selected.set_name}</h3>
            <button onClick={() => setSelected(null)} className="text-slate-400 text-xs">Close</button>
          </div>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-slate-500">Input Transactions</label>
              <pre className="text-xs bg-white rounded p-2 mt-1 max-h-40 overflow-auto border">
                {JSON.stringify(selected.input_transactions, null, 2)}
              </pre>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500">Expected Output</label>
              <pre className="text-xs bg-white rounded p-2 mt-1 max-h-40 overflow-auto border">
                {JSON.stringify(selected.expected_output, null, 2)}
              </pre>
            </div>
            {selected.reference_transactions != null && (
              <div>
                <label className="text-xs font-medium text-slate-500">Reference Transactions</label>
                <pre className="text-xs bg-white rounded p-2 mt-1 max-h-40 overflow-auto border">
                  {JSON.stringify(selected.reference_transactions, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// --- Prompts Tab ---
function PromptsTab() {
  const [prompts, setPrompts] = useState<ClassificationPrompt[]>([])
  const [selected, setSelected] = useState<ClassificationPrompt | null>(null)
  const [editName, setEditName] = useState('')
  const [editTemplate, setEditTemplate] = useState('')
  const [editModel, setEditModel] = useState('gemini-2.5-pro')
  const [saving, setSaving] = useState(false)
  const { addToast } = useToast()

  const isDirty = useMemo(() => {
    if (!selected) return false
    return editName !== selected.name || editTemplate !== selected.prompt_template || editModel !== selected.model
  }, [selected, editName, editTemplate, editModel])

  useEffect(() => {
    api.listClassificationPrompts().then(setPrompts)
  }, [])

  const selectPrompt = (p: ClassificationPrompt) => {
    setSelected(p)
    setEditName(p.name)
    setEditTemplate(p.prompt_template)
    setEditModel(p.model)
  }

  const handleSave = async () => {
    if (!selected) return
    setSaving(true)
    try {
      const updated = await api.updateClassificationPrompt(selected.id, {
        name: editName,
        prompt_template: editTemplate,
        model: editModel,
      })
      setPrompts((prev) => prev.map((p) => (p.id === updated.id ? updated : p)))
      setSelected(updated)
      addToast('Prompt saved', 'success')
    } catch {
      addToast('Failed to save', 'error')
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    const created = await api.createClassificationPrompt({
      name: 'New Classification Prompt',
      prompt_template: 'Classify the following transactions:\n\n{{input_transactions}}\n\nRespond with a JSON array.',
    })
    setPrompts((prev) => [created, ...prev])
    selectPrompt(created)
  }

  return (
    <div className="flex h-full">
      <div className="w-64 border-r border-slate-200 p-3 overflow-auto">
        <button onClick={handleCreate} className="w-full bg-indigo-600 text-white px-3 py-1.5 rounded text-sm mb-3">
          New Prompt
        </button>
        <div className="space-y-1">
          {prompts.map((p) => (
            <div
              key={p.id}
              onClick={() => selectPrompt(p)}
              className={`px-3 py-2 rounded text-sm cursor-pointer ${selected?.id === p.id ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-slate-50'}`}
            >
              {p.name}
            </div>
          ))}
        </div>
      </div>

      {selected ? (
        <div className="flex-1 p-4 overflow-auto">
          <div className="space-y-4 max-w-3xl">
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">Name</label>
              <input value={editName} onChange={(e) => setEditName(e.target.value)} className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm" />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">Model</label>
              <select value={editModel} onChange={(e) => setEditModel(e.target.value)} className="border border-slate-300 rounded px-3 py-1.5 text-sm">
                <option value="gemini-2.5-pro">gemini-2.5-pro</option>
                <option value="gemini-2.5-flash">gemini-2.5-flash</option>
                <option value="gemini-2.0-flash">gemini-2.0-flash</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-slate-500 mb-1 block">
                Prompt Template (placeholders: {'{{input_transactions}}'}, {'{{reference_list_1}}'}, etc.)
              </label>
              <PromptEditor value={editTemplate} onChange={setEditTemplate} height="300px" />
            </div>
            <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
              {isDirty && <span className="text-xs text-amber-500">• Unsaved changes</span>}
              <button
                onClick={handleSave}
                disabled={!isDirty || saving}
                className="ml-auto bg-indigo-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">Select or create a prompt</div>
      )}
    </div>
  )
}

// --- Classification Runs Tab ---
function ClassificationRunsTab() {
  const [prompts, setPrompts] = useState<ClassificationPrompt[]>([])
  const [goldenSets, setGoldenSets] = useState<GoldenTransaction[]>([])
  const [runs, setRuns] = useState<ClassificationRun[]>([])
  const [selectedRun, setSelectedRun] = useState<ClassificationRun | null>(null)
  const [results, setResults] = useState<ClassificationResult[]>([])
  const [selectedPromptId, setSelectedPromptId] = useState('')
  const [selectedSetName, setSelectedSetName] = useState('')
  const [launching, setLaunching] = useState(false)
  const pollingRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())
  const { addToast } = useToast()

  const pollRun = useCallback((runId: string) => {
    if (pollingRef.current.has(runId)) return

    const interval = setInterval(async () => {
      try {
        const latest = await api.getClassificationRun(runId)
        setRuns((prev) => prev.map((r) => (r.id === runId ? latest : r)))

        if (latest.status !== 'running') {
          clearInterval(interval)
          pollingRef.current.delete(runId)

          if (latest.status === 'completed') {
            setSelectedRun(latest)
            const res = await api.getClassificationResults(runId)
            setResults(res)
            addToast('Classification run completed', 'success')
          } else if (latest.status === 'failed') {
            addToast('Classification run failed', 'error')
          }
        }
      } catch {
        // Network error — keep polling
      }
    }, 2000)

    pollingRef.current.set(runId, interval)
  }, [addToast])

  useEffect(() => {
    api.listClassificationPrompts().then(setPrompts)
    api.listGoldenSets().then(setGoldenSets)
    api.listClassificationRuns().then((loadedRuns) => {
      setRuns(loadedRuns)
      loadedRuns.filter((r) => r.status === 'running').forEach((r) => pollRun(r.id))
    })
  }, [pollRun])

  useEffect(() => {
    const ref = pollingRef.current
    return () => {
      ref.forEach((interval) => clearInterval(interval))
      ref.clear()
    }
  }, [])

  const setNames = [...new Set(goldenSets.map((g) => g.set_name))]

  const handleLaunch = async () => {
    if (!selectedPromptId || !selectedSetName) return
    setLaunching(true)
    try {
      const run = await api.startClassificationRun(selectedPromptId, selectedSetName)
      setRuns((prev) => [run, ...prev])
      pollRun(run.id)
    } finally {
      setLaunching(false)
    }
  }

  const handleSelectRun = async (run: ClassificationRun) => {
    const latest = await api.getClassificationRun(run.id)
    setSelectedRun(latest)
    const res = await api.getClassificationResults(run.id)
    setResults(res)
  }

  return (
    <div className="p-4">
      {/* Launch Section */}
      <div className="mb-6 bg-white border border-slate-200 rounded-lg p-4">
        <h3 className="text-sm font-medium mb-3">Launch Classification Run</h3>
        <div className="flex items-end gap-3">
          <div>
            <label className="text-xs text-slate-500 block mb-1">Prompt</label>
            <select value={selectedPromptId} onChange={(e) => setSelectedPromptId(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm">
              <option value="">Select...</option>
              {prompts.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Golden Set</label>
            <select value={selectedSetName} onChange={(e) => setSelectedSetName(e.target.value)} className="border border-slate-300 rounded px-2 py-1.5 text-sm">
              <option value="">Select...</option>
              {setNames.map((name) => <option key={name} value={name}>{name}</option>)}
            </select>
          </div>
          <button
            onClick={handleLaunch}
            disabled={launching || !selectedPromptId || !selectedSetName}
            className="bg-indigo-600 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
          >
            {launching ? 'Launching...' : 'Run Evaluation'}
          </button>
        </div>
      </div>

      {/* Run History */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h3 className="text-sm font-medium mb-2">Run History</h3>
          <DataTable
            columns={[
              { key: 'created_at', header: 'Date', sortable: true },
              { key: 'golden_set_name', header: 'Set' },
              { key: 'status', header: 'Status', render: (r) => <StatusBadge status={(r as ClassificationRun).status} /> },
              { key: 'metrics', header: 'Match Rate', render: (r) => {
                const run = r as ClassificationRun
                return run.metrics?.exact_match_rate != null ? `${(run.metrics.exact_match_rate * 100).toFixed(1)}%` : '-'
              }},
            ]}
            data={runs}
            onRowClick={(row) => handleSelectRun(row as ClassificationRun)}
          />
        </div>

        {selectedRun && (
          <div>
            <h3 className="text-sm font-medium mb-2">Run Detail</h3>
            <div className="flex items-center gap-2 mb-3">
              <StatusBadge status={selectedRun.status} />
              <span className="text-xs text-slate-500">{selectedRun.golden_set_name}</span>
            </div>
            {selectedRun.metrics && (
              <MetricsCard
                title="Classification Metrics"
                metrics={{
                  exact_match_rate: selectedRun.metrics.exact_match_rate,
                  total: selectedRun.metrics.total,
                  exact_matches: selectedRun.metrics.exact_matches,
                }}
              />
            )}
            {selectedRun.metrics?.per_category && (
              <div className="mt-3">
                <h4 className="text-xs font-medium text-slate-500 mb-2">Per-Category</h4>
                <div className="grid grid-cols-2 gap-2">
                  {Object.entries(selectedRun.metrics.per_category).map(([cat, m]) => (
                    <div key={cat} className="bg-slate-50 rounded p-2 text-xs">
                      <div className="font-medium">{cat}</div>
                      <div>P: {(m.precision * 100).toFixed(0)}% R: {(m.recall * 100).toFixed(0)}% F1: {(m.f1 * 100).toFixed(0)}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
            <div className="mt-3">
              <h4 className="text-xs font-medium text-slate-500 mb-2">Per-Entry Results</h4>
              <div className="space-y-1 max-h-96 overflow-auto">
                {results.map((r) => (
                  <details key={r.id} className="border border-slate-200 rounded text-xs">
                    <summary className="px-3 py-1.5 cursor-pointer bg-slate-50">
                      {r.golden_id.slice(0, 8)}...
                    </summary>
                    <div className="px-3 py-2">
                      <pre className="whitespace-pre-wrap max-h-32 overflow-auto">
                        {JSON.stringify(r.predicted_output, null, 2)}
                      </pre>
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
