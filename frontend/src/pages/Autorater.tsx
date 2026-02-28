import { useState, useEffect, useRef, useCallback } from 'react'
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
  const [editingTags, setEditingTags] = useState('')
  const [editingLabels, setEditingLabels] = useState<Record<string, string>>({})

  useEffect(() => {
    api.listTranscripts(tagFilter || undefined).then(setTranscripts)
  }, [tagFilter])

  const handleSelect = (t: Transcript) => {
    setSelected(t)
    setEditingTags((t.tags ?? []).join(', '))
    setEditingLabels(t.labels ?? {})
  }

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

  const handleSaveTags = async () => {
    if (!selected) return
    const tags = editingTags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
    // Only keep labels for tags that still exist on the transcript
    const cleanedLabels: Record<string, string> = {}
    for (const tag of tags) {
      if (editingLabels[tag]) cleanedLabels[tag] = editingLabels[tag]
    }
    const updated = await api.updateTranscript(selected.id, { tags, labels: cleanedLabels })
    setTranscripts((prev) => prev.map((t) => (t.id === updated.id ? updated : t)))
    setSelected(updated)
    setEditingLabels(updated.labels ?? {})
  }

  const toggleLabel = (tag: string, value: 'P' | 'N') => {
    setEditingLabels((prev) => {
      const next = { ...prev }
      if (next[tag] === value) {
        delete next[tag]
      } else {
        next[tag] = value
      }
      return next
    })
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
            { key: 'tags', header: 'Tags', render: (r) => {
              const t = r as Transcript
              return (t.tags ?? []).map((tag) => (
                <span key={tag} className="inline-block mr-1 text-xs bg-blue-50 text-blue-600 rounded px-1">{tag}</span>
              ))
            }},
            { key: 'created_at', header: 'Created', sortable: true },
          ]}
          data={transcripts}
          onRowClick={(row) => handleSelect(row as Transcript)}
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
            <label className="text-xs font-medium text-gray-500 block mb-1">Tags (comma-separated)</label>
            <div className="flex gap-1">
              <input
                value={editingTags}
                onChange={(e) => setEditingTags(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleSaveTags() }}
                placeholder="polite, accurate, refund..."
                className="flex-1 border border-gray-300 rounded px-2 py-1 text-xs"
              />
              <button
                onClick={handleSaveTags}
                className="bg-blue-600 text-white px-2 py-1 rounded text-xs"
              >
                Save
              </button>
            </div>
            {(selected.tags ?? []).length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {selected.tags!.map((tag) => {
                  const label = editingLabels[tag]
                  return (
                    <span key={tag} className={`inline-block text-xs rounded px-1.5 py-0.5 ${
                      label === 'P' ? 'bg-green-100 text-green-700' :
                      label === 'N' ? 'bg-red-100 text-red-700' :
                      'bg-blue-50 text-blue-600'
                    }`}>{tag}{label ? ` (${label})` : ''}</span>
                  )
                })}
              </div>
            )}
          </div>

          {(selected.tags ?? []).length > 0 && (
            <div className="mb-3">
              <label className="text-xs font-medium text-gray-500 block mb-1">Evaluation Annotations</label>
              <p className="text-xs text-gray-400 mb-2">Mark each tag as P (positive — should pass) or N (negative — should fail) for eval metrics.</p>
              <div className="space-y-1">
                {selected.tags!.map((tag) => {
                  const label = editingLabels[tag]
                  return (
                    <div key={tag} className="flex items-center gap-1.5 text-xs">
                      <span className="text-gray-700 w-24 truncate">{tag}</span>
                      <button
                        onClick={() => toggleLabel(tag, 'P')}
                        className={`px-2 py-0.5 rounded ${label === 'P' ? 'bg-green-500 text-white' : 'bg-gray-100 text-gray-500 hover:bg-green-100'}`}
                      >
                        P
                      </button>
                      <button
                        onClick={() => toggleLabel(tag, 'N')}
                        className={`px-2 py-0.5 rounded ${label === 'N' ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-500 hover:bg-red-100'}`}
                      >
                        N
                      </button>
                      {label && (
                        <span className={`text-xs ${label === 'P' ? 'text-green-600' : 'text-red-600'}`}>
                          {label === 'P' ? 'Positive' : 'Negative'}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
              <p className="text-xs text-gray-400 mt-1">Click Save above to persist annotations.</p>
            </div>
          )}
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
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

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
    if (!selected) return
    setSaving(true)
    setSaveError('')
    try {
      const updated = await api.updateAutorater(selected.id, {
        name: editName,
        prompt: editPrompt,
        model: editModel,
      })
      setAutoraters((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
      setSelected(updated)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save')
    } finally {
      setSaving(false)
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
            <div className="flex items-center gap-3">
              <button
                onClick={handleSave}
                disabled={saving}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save'}
              </button>
              {saveError && <span className="text-red-600 text-sm">{saveError}</span>}
            </div>
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
  const [selectedTranscriptIds, setSelectedTranscriptIds] = useState<Set<string>>(new Set())
  const [showTranscripts, setShowTranscripts] = useState(false)
  const [runs, setRuns] = useState<EvalRun[]>([])
  const [selectedRun, setSelectedRun] = useState<EvalRun | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [selectedAutoraterId, setSelectedAutoraterId] = useState('')
  const [launching, setLaunching] = useState(false)
  const pollingRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map())

  // Eval tags for per-tag P/R (replaces pass_tags/fail_tags)
  const [selectedEvalTags, setSelectedEvalTags] = useState<Set<string>>(new Set())
  const [showEvalTags, setShowEvalTags] = useState(false)

  // Collect all unique tags from selected transcripts
  const selectedTranscripts = transcripts.filter((t) => selectedTranscriptIds.has(t.id))
  const allTags = Array.from(new Set(transcripts.flatMap((t) => t.tags ?? [])))

  // Tags that have P/N annotations in any selected transcript
  const annotatedTags = Array.from(new Set(
    selectedTranscripts.flatMap((t) => {
      const labels = t.labels ?? {}
      return Object.entries(labels)
        .filter(([, v]) => v === 'P' || v === 'N')
        .map(([k]) => k)
    })
  ))

  // Tag counts for chips
  const tagCounts: Record<string, number> = {}
  for (const t of transcripts) {
    for (const tag of t.tags ?? []) {
      tagCounts[tag] = (tagCounts[tag] ?? 0) + 1
    }
  }

  // Toggle all transcripts with a given tag
  const toggleTagChip = (tag: string) => {
    const idsWithTag = transcripts.filter((t) => (t.tags ?? []).includes(tag)).map((t) => t.id)
    const allSelected = idsWithTag.every((id) => selectedTranscriptIds.has(id))
    const next = new Set(selectedTranscriptIds)
    if (allSelected) {
      idsWithTag.forEach((id) => next.delete(id))
    } else {
      idsWithTag.forEach((id) => next.add(id))
    }
    setSelectedTranscriptIds(next)
  }

  const isTagFullySelected = (tag: string) => {
    const idsWithTag = transcripts.filter((t) => (t.tags ?? []).includes(tag)).map((t) => t.id)
    return idsWithTag.length > 0 && idsWithTag.every((id) => selectedTranscriptIds.has(id))
  }

  // Poll a running eval run until it completes
  const pollRun = useCallback((runId: string) => {
    if (pollingRef.current.has(runId)) return

    const interval = setInterval(async () => {
      try {
        const latest = await api.getEvalRun(runId)
        setRuns((prev) => prev.map((r) => (r.id === runId ? latest : r)))

        if (latest.status !== 'running') {
          clearInterval(interval)
          pollingRef.current.delete(runId)

          if (latest.status === 'completed') {
            setSelectedRun(latest)
            const res = await api.getEvalResults(runId)
            setResults(res)
          }
        }
      } catch {
        // Network error — keep polling
      }
    }, 2000)

    pollingRef.current.set(runId, interval)
  }, [])

  useEffect(() => {
    api.listAutoraters().then(setAutoraters)
    api.listTranscripts().then((ts) => {
      setTranscripts(ts)
      setSelectedTranscriptIds(new Set(ts.map((t) => t.id)))
    })
    api.listEvalRuns().then((loadedRuns) => {
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

  const handleLaunch = async () => {
    if (!selectedAutoraterId || !selectedTranscriptIds.size) return
    setLaunching(true)
    try {
      const run = await api.startEvalRun(
        selectedAutoraterId,
        Array.from(selectedTranscriptIds),
        selectedEvalTags.size ? Array.from(selectedEvalTags) : undefined,
      )
      setRuns((prev) => [run, ...prev])
      pollRun(run.id)
    } finally {
      setLaunching(false)
    }
  }

  const handleSelectRun = async (run: EvalRun) => {
    const latest = await api.getEvalRun(run.id)
    setSelectedRun(latest)
    const res = await api.getEvalResults(run.id)
    setResults(res)
  }

  // Annotation coverage for a tag across selected transcripts
  const annotationCoverage = (tag: string) => {
    const withTag = selectedTranscripts.filter((t) => (t.tags ?? []).includes(tag))
    const annotated = withTag.filter((t) => {
      const v = (t.labels ?? {})[tag]
      return v === 'P' || v === 'N'
    })
    return { annotated: annotated.length, total: withTag.length }
  }

  return (
    <div className="p-4">
      {/* Launch Section */}
      <div className="mb-6 bg-white border border-gray-200 rounded-lg p-4">
        <h3 className="text-sm font-medium mb-3">Launch Eval Run</h3>
        <div className="flex items-end gap-3 mb-3">
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
          <button
            onClick={() => setShowTranscripts(!showTranscripts)}
            className="text-xs text-blue-600 hover:text-blue-800 py-1.5"
          >
            {selectedTranscriptIds.size} of {transcripts.length} transcripts {showTranscripts ? '▲' : '▼'}
          </button>
          <button
            onClick={() => setShowEvalTags(!showEvalTags)}
            className={`text-xs py-1.5 ${selectedEvalTags.size ? 'text-green-600 hover:text-green-800' : 'text-gray-500 hover:text-gray-700'}`}
          >
            {selectedEvalTags.size ? `Eval tags: ${selectedEvalTags.size} selected` : 'Evaluation Tags'} {showEvalTags ? '▲' : '▼'}
          </button>
          <button
            onClick={handleLaunch}
            disabled={launching || !selectedAutoraterId || !selectedTranscriptIds.size}
            className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm disabled:opacity-50"
          >
            {launching ? 'Launching...' : 'Run Evaluation'}
          </button>
        </div>

        {showTranscripts && (
          <div className="mb-3">
            {/* Tag chips for quick transcript filtering */}
            {allTags.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2">
                {allTags.map((tag) => {
                  const selected = isTagFullySelected(tag)
                  return (
                    <button
                      key={tag}
                      onClick={() => toggleTagChip(tag)}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        selected
                          ? 'bg-blue-500 text-white border-blue-500'
                          : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                      }`}
                    >
                      {tag} ({tagCounts[tag]})
                    </button>
                  )
                })}
              </div>
            )}
            <div className="border border-gray-200 rounded max-h-56 overflow-auto">
            <DataTable
              columns={[
                { key: 'name', header: 'Name', sortable: true },
                { key: 'source', header: 'Source', render: (r) => <StatusBadge status={(r as Transcript).source} /> },
                { key: 'tags', header: 'Tags', render: (r) => {
                  const t = r as Transcript
                  return (t.tags ?? []).map((tag) => (
                    <span key={tag} className="inline-block mr-1 text-xs bg-blue-50 text-blue-600 rounded px-1">{tag}</span>
                  ))
                }},
              ]}
              data={transcripts}
              selectable
              selectedIds={selectedTranscriptIds}
              onSelectionChange={setSelectedTranscriptIds}
            />
            </div>
          </div>
        )}

        {showEvalTags && (
          <div className="border border-gray-200 rounded p-3">
            <p className="text-xs text-gray-500 mb-2">
              Select tags to compute per-tag precision/recall. Only tags with P/N annotations on selected transcripts are shown.
            </p>
            {annotatedTags.length > 0 ? (
              <div className="space-y-1.5">
                {annotatedTags.map((tag) => {
                  const coverage = annotationCoverage(tag)
                  return (
                    <label key={tag} className="flex items-center gap-2 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedEvalTags.has(tag)}
                        onChange={() => {
                          const next = new Set(selectedEvalTags)
                          if (next.has(tag)) next.delete(tag); else next.add(tag)
                          setSelectedEvalTags(next)
                        }}
                        className="rounded border-gray-300"
                      />
                      <span className="text-gray-700">{tag}</span>
                      <span className="text-gray-400">— {coverage.annotated} of {coverage.total} annotated</span>
                    </label>
                  )
                })}
              </div>
            ) : (
              <p className="text-xs text-gray-400 italic">No P/N annotations found on selected transcripts. Annotate transcripts in the Transcripts tab first.</p>
            )}
          </div>
        )}
      </div>

      {/* Run History */}
      <div className="grid grid-cols-[1fr_1fr] gap-4">
        <div>
          <h3 className="text-sm font-medium mb-2">Run History</h3>
          <DataTable
            columns={[
              { key: 'created_at', header: 'Date', sortable: true },
              { key: 'status', header: 'Status', render: (r) => <StatusBadge status={(r as EvalRun).status} /> },
              { key: 'pass_rate', header: 'Pass Rate', render: (r) => {
                const run = r as EvalRun
                return run.metrics?.pass_rate != null ? `${(run.metrics.pass_rate * 100).toFixed(1)}%` : '-'
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
              {selectedRun.eval_tags && selectedRun.eval_tags.length > 0 && (
                <span className="text-xs text-gray-400">
                  eval tags: {selectedRun.eval_tags.join(', ')}
                </span>
              )}
            </div>
            {selectedRun.metrics && (
              <>
                <MetricsCard
                  title="Pass Rate"
                  metrics={{
                    pass_rate: selectedRun.metrics.pass_rate,
                    passed: selectedRun.metrics.passed,
                    total: selectedRun.metrics.total,
                  }}
                />
                {selectedRun.metrics.per_tag && Object.entries(selectedRun.metrics.per_tag).map(([tag, m]) => (
                  <div key={tag} className="mt-3">
                    <MetricsCard
                      title={`Tag: ${tag}`}
                      metrics={{
                        precision: m.precision,
                        recall: m.recall,
                        f1: m.f1,
                      }}
                    />
                    <div className="mt-1 grid grid-cols-4 gap-2 text-xs text-center">
                      <div className="bg-green-50 rounded p-1"><div className="text-green-700 font-medium">{m.tp}</div><div className="text-gray-400">TP</div></div>
                      <div className="bg-red-50 rounded p-1"><div className="text-red-700 font-medium">{m.fp}</div><div className="text-gray-400">FP</div></div>
                      <div className="bg-orange-50 rounded p-1"><div className="text-orange-700 font-medium">{m.fn}</div><div className="text-gray-400">FN</div></div>
                      <div className="bg-gray-50 rounded p-1"><div className="text-gray-700 font-medium">{m.tn}</div><div className="text-gray-400">TN</div></div>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">{m.annotated} annotated transcripts</div>
                  </div>
                ))}
              </>
            )}
            <div className="mt-3">
              <h4 className="text-xs font-medium text-gray-500 mb-2">Per-Transcript Results</h4>
              <div className="space-y-1 max-h-96 overflow-auto">
                {results.map((r) => {
                  const assessment = (r.predicted_labels as Record<string, string>)?.assessment
                  const gtLabels = r.ground_truth_labels as Record<string, string>
                  const hasAnnotations = Object.keys(gtLabels).length > 0
                  const bgClass = assessment === 'pass' ? 'bg-blue-50' : 'bg-orange-50'

                  return (
                    <details key={r.id} className="border border-gray-200 rounded text-xs">
                      <summary className={`px-3 py-1.5 cursor-pointer ${bgClass}`}>
                        {r.transcript_id.slice(0, 8)}... — {assessment ?? 'unknown'}
                        {hasAnnotations && (
                          <span className="ml-2">
                            {Object.entries(gtLabels).map(([tag, label]) => {
                              const expected = label === 'P' ? 'pass' : 'fail'
                              const agree = assessment === expected
                              return (
                                <span key={tag} className={`inline-block ml-1 px-1 rounded ${agree ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                  {tag}: {agree ? 'ok' : 'miss'}
                                </span>
                              )
                            })}
                          </span>
                        )}
                      </summary>
                      <div className="px-3 py-2 space-y-1">
                        <div><span className="text-gray-500">Response:</span> {JSON.stringify(r.predicted_labels)}</div>
                        {hasAnnotations && <div><span className="text-gray-500">Annotations:</span> {JSON.stringify(gtLabels)}</div>}
                      </div>
                    </details>
                  )
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
