import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Agent, AgentVersion, AgentTemplateResponse } from '../api/types'
import DataTable from '../components/DataTable'
import PromptEditor from '../components/PromptEditor'
import StatusBadge from '../components/StatusBadge'

type Tab = 'overview' | 'template' | 'versions'

export default function Agents() {
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [agents, setAgents] = useState<Agent[]>([])
  const [selected, setSelected] = useState<Agent | null>(null)

  const loadAgents = async () => {
    const list = await api.listAgents()
    setAgents(list)
    if (selected) {
      const updated = list.find((a) => a.id === selected.id)
      if (updated) setSelected(updated)
    }
  }

  useEffect(() => {
    loadAgents()
  }, [])

  const handleSelect = (a: Agent) => {
    setSelected(a)
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: 'Overview' },
    { key: 'template', label: 'Template & Variables' },
    { key: 'versions', label: 'Versions' },
  ]

  return (
    <div className="h-full flex flex-col">
      <div className="flex border-b border-gray-200 bg-white px-4 shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto">
        {activeTab === 'overview' && (
          <OverviewTab
            agents={agents}
            selected={selected}
            onSelect={handleSelect}
            onRefresh={loadAgents}
          />
        )}
        {activeTab === 'template' && <TemplateTab agent={selected} />}
        {activeTab === 'versions' && (
          <VersionsTab agent={selected} onRefresh={loadAgents} />
        )}
      </div>
    </div>
  )
}

// --- Overview Tab ---
function OverviewTab({
  agents,
  selected,
  onSelect,
  onRefresh,
}: {
  agents: Agent[]
  selected: Agent | null
  onSelect: (a: Agent) => void
  onRefresh: () => Promise<void>
}) {
  const [folders, setFolders] = useState<string[]>([])
  const [importFolder, setImportFolder] = useState('')
  const [importing, setImporting] = useState(false)
  const [importMsg, setImportMsg] = useState('')

  useEffect(() => {
    api.listAgentFolders().then(setFolders).catch(() => setFolders([]))
  }, [])

  const handleImport = async (folder?: string) => {
    const target = folder || importFolder
    if (!target) return
    setImporting(true)
    setImportMsg('')
    try {
      const result = await api.importAgent(target)
      setImportMsg(result.message)
      await onRefresh()
    } catch (e) {
      setImportMsg(e instanceof Error ? e.message : 'Import failed')
    } finally {
      setImporting(false)
    }
  }

  const handleDelete = async () => {
    if (!selected) return
    await api.deleteAgent(selected.id)
    onSelect(null as unknown as Agent)
    await onRefresh()
  }

  const columns = [
    { key: 'name', header: 'Name' },
    { key: 'model', header: 'Model' },
    {
      key: 'agent_folder',
      header: 'Folder',
      render: (r: Agent) => r.agent_folder || '-',
    },
    {
      key: 'active_version_id',
      header: 'Source',
      render: (r: Agent) =>
        r.agent_folder ? (
          <StatusBadge status="file" />
        ) : (
          <StatusBadge status="ui" />
        ),
    },
  ]

  return (
    <div className="h-full flex">
      {/* Left — agent list */}
      <div className="w-96 border-r border-gray-200 flex flex-col bg-white">
        <div className="p-3 border-b border-gray-200">
          <h2 className="text-sm font-semibold text-gray-700">Agents</h2>
        </div>
        <div className="flex-1 overflow-auto">
          <DataTable
            columns={columns}
            data={agents}
            onRowClick={onSelect}
            emptyMessage="No agents"
          />
        </div>
      </div>

      {/* Right — detail + import */}
      <div className="flex-1 p-6 overflow-auto">
        {selected ? (
          <div className="max-w-2xl space-y-4">
            <h3 className="text-lg font-semibold text-gray-800">{selected.name}</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Model:</span>{' '}
                <span className="font-medium">{selected.model}</span>
              </div>
              <div>
                <span className="text-gray-500">Folder:</span>{' '}
                <span className="font-medium">{selected.agent_folder || 'None'}</span>
              </div>
              <div>
                <span className="text-gray-500">Active Version:</span>{' '}
                <span className="font-medium">{selected.active_version_id ? 'Yes' : 'None'}</span>
              </div>
              <div>
                <span className="text-gray-500">Created:</span>{' '}
                <span className="font-medium">
                  {new Date(selected.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              {selected.agent_folder && (
                <button
                  onClick={() => handleImport(selected.agent_folder!)}
                  disabled={importing}
                  className="px-3 py-1.5 text-sm font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {importing ? 'Importing...' : 'Re-import from Files'}
                </button>
              )}
              <button
                onClick={handleDelete}
                className="px-3 py-1.5 text-sm font-medium bg-red-600 text-white rounded hover:bg-red-700"
              >
                Delete Agent
              </button>
            </div>

            {importMsg && (
              <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded">{importMsg}</div>
            )}
          </div>
        ) : (
          <div className="text-gray-400 text-sm mb-6">Select an agent to view details</div>
        )}

        {/* Import section */}
        <div className="mt-8 pt-6 border-t border-gray-200 max-w-2xl">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Import Agent from Folder</h3>
          {folders.length > 0 ? (
            <div className="flex gap-2 items-center">
              <select
                value={importFolder}
                onChange={(e) => setImportFolder(e.target.value)}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Select folder...</option>
                {folders.map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
              <button
                onClick={() => handleImport()}
                disabled={importing || !importFolder}
                className="px-3 py-1.5 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {importing ? 'Importing...' : 'Import'}
              </button>
            </div>
          ) : (
            <div className="text-sm text-gray-400">No agent folders available</div>
          )}
          {importMsg && !selected && (
            <div className="text-sm text-gray-600 bg-gray-50 p-2 rounded mt-2">{importMsg}</div>
          )}
        </div>
      </div>
    </div>
  )
}

// --- Template & Variables Tab ---
function TemplateTab({ agent }: { agent: Agent | null }) {
  const [template, setTemplate] = useState<AgentTemplateResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!agent?.active_version_id) {
      setTemplate(null)
      return
    }
    setLoading(true)
    setError('')
    api
      .getAgentTemplate(agent.id)
      .then(setTemplate)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load template'))
      .finally(() => setLoading(false))
  }, [agent?.id, agent?.active_version_id])

  if (!agent) {
    return <div className="p-6 text-gray-400 text-sm">Select an agent in the Overview tab</div>
  }

  if (!agent.active_version_id) {
    return (
      <div className="p-6 text-gray-400 text-sm">
        No active version set. Import or create a version first.
      </div>
    )
  }

  if (loading) {
    return <div className="p-6 text-gray-400 text-sm">Loading template...</div>
  }

  if (error) {
    return <div className="p-6 text-red-600 text-sm">{error}</div>
  }

  if (!template) return null

  const varDefs = template.variable_definitions ?? []

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {/* Raw template */}
      {template.raw_template && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Raw Template (.ftl)</h3>
          <PromptEditor value={template.raw_template} readOnly height="250px" />
        </section>
      )}

      {/* Variables */}
      {varDefs.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Variables</h3>
          <div className="border border-gray-200 rounded overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Name</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Type</th>
                  <th className="text-left px-3 py-2 font-medium text-gray-600">Value Preview</th>
                </tr>
              </thead>
              <tbody>
                {varDefs.map((def: Record<string, unknown>, i: number) => {
                  const name = String(def.name ?? '')
                  const type = String(def.type ?? 'static')
                  const resolved = template.variables?.[name]
                  const preview =
                    resolved !== undefined
                      ? typeof resolved === 'string'
                        ? resolved.slice(0, 120)
                        : JSON.stringify(resolved).slice(0, 120)
                      : '-'
                  return (
                    <tr key={i} className="border-t border-gray-100 hover:bg-gray-50">
                      <td className="px-3 py-2 font-mono text-xs">{name}</td>
                      <td className="px-3 py-2">
                        <StatusBadge status={type} />
                      </td>
                      <td className="px-3 py-2 text-gray-600 truncate max-w-xs">{preview}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* Rendered prompt */}
      <section>
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Rendered System Prompt</h3>
        <PromptEditor value={template.system_prompt} readOnly height="300px" />
      </section>

      {/* Tools */}
      {template.tool_details && template.tool_details.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Tools</h3>
          <div className="space-y-2">
            {template.tool_details.map((tool, i) => (
              <div key={i} className="border border-gray-200 rounded p-3">
                <div className="font-medium text-sm">{tool.name}</div>
                {tool.usageGuidelines && (
                  <div className="text-xs text-gray-500 mt-1">{tool.usageGuidelines}</div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Widgets */}
      {template.widget_details && template.widget_details.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Widgets</h3>
          <div className="space-y-2">
            {template.widget_details.map((w, i) => (
              <div key={i} className="border border-gray-200 rounded p-3">
                <div className="font-medium text-sm">{w.name}</div>
                <div className="text-xs text-gray-500 mt-1">{w.description}</div>
                {w.example && (
                  <pre className="text-xs bg-gray-50 p-2 mt-1 rounded overflow-auto">
                    {w.example}
                  </pre>
                )}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

// --- Versions Tab ---
function VersionsTab({
  agent,
  onRefresh,
}: {
  agent: Agent | null
  onRefresh: () => Promise<void>
}) {
  const [versions, setVersions] = useState<AgentVersion[]>([])
  const [selected, setSelected] = useState<AgentVersion | null>(null)
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [newLabel, setNewLabel] = useState('')
  const [newPrompt, setNewPrompt] = useState('')
  const [creating, setCreating] = useState(false)

  const loadVersions = async () => {
    if (!agent) return
    setLoading(true)
    try {
      const list = await api.listAgentVersions(agent.id)
      setVersions(list)
    } catch {
      setVersions([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setSelected(null)
    loadVersions()
  }, [agent?.id])

  const handleSetActive = async (versionId: string) => {
    if (!agent) return
    await api.setActiveVersion(agent.id, versionId)
    await onRefresh()
    await loadVersions()
  }

  const handleCreate = async () => {
    if (!agent || !newLabel.trim()) return
    setCreating(true)
    try {
      await api.createAgentVersion(agent.id, {
        version_label: newLabel,
        system_prompt: newPrompt,
      })
      setShowCreate(false)
      setNewLabel('')
      setNewPrompt('')
      await loadVersions()
      await onRefresh()
    } finally {
      setCreating(false)
    }
  }

  const handleReimport = async () => {
    if (!agent?.agent_folder) return
    await api.importAgent(agent.agent_folder)
    await onRefresh()
    await loadVersions()
  }

  if (!agent) {
    return <div className="p-6 text-gray-400 text-sm">Select an agent in the Overview tab</div>
  }

  const columns = [
    { key: 'version_label', header: 'Label' },
    {
      key: 'source',
      header: 'Source',
      render: (r: AgentVersion) => <StatusBadge status={r.source} />,
    },
    {
      key: 'created_at',
      header: 'Created',
      render: (r: AgentVersion) => new Date(r.created_at).toLocaleDateString(),
    },
    {
      key: 'id',
      header: 'Active',
      render: (r: AgentVersion) =>
        r.id === agent.active_version_id ? (
          <span className="text-green-600 font-medium text-xs">Active</span>
        ) : (
          <button
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation()
              handleSetActive(r.id)
            }}
            className="text-blue-600 hover:text-blue-800 text-xs font-medium"
          >
            Set Active
          </button>
        ),
    },
  ]

  return (
    <div className="h-full flex">
      {/* Left — version list */}
      <div className="w-[480px] border-r border-gray-200 flex flex-col bg-white">
        <div className="p-3 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">
            Versions — {agent.name}
          </h2>
          <div className="flex gap-2">
            {agent.agent_folder && (
              <button
                onClick={handleReimport}
                className="px-2 py-1 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700"
              >
                Re-import
              </button>
            )}
            <button
              onClick={() => setShowCreate(true)}
              className="px-2 py-1 text-xs font-medium bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Create Version
            </button>
          </div>
        </div>
        {loading ? (
          <div className="p-4 text-gray-400 text-sm">Loading...</div>
        ) : (
          <div className="flex-1 overflow-auto">
            <DataTable
              columns={columns}
              data={versions}
              onRowClick={setSelected}
              emptyMessage="No versions"
            />
          </div>
        )}
      </div>

      {/* Right — version detail or create form */}
      <div className="flex-1 p-6 overflow-auto">
        {showCreate ? (
          <div className="max-w-2xl space-y-4">
            <h3 className="text-sm font-semibold text-gray-700">Create New Version</h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Version Label</label>
              <input
                type="text"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g. v2-tweaked-tools"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">System Prompt</label>
              <PromptEditor value={newPrompt} onChange={setNewPrompt} height="300px" />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={creating || !newLabel.trim()}
                className="px-4 py-1.5 text-sm font-medium bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-1.5 text-sm font-medium bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : selected ? (
          <div className="max-w-3xl space-y-4">
            <div className="flex items-center gap-3">
              <h3 className="text-lg font-semibold text-gray-800">{selected.version_label}</h3>
              <StatusBadge status={selected.source} />
              {selected.is_base && (
                <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">
                  Base
                </span>
              )}
              {selected.id === agent.active_version_id && (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                  Active
                </span>
              )}
            </div>
            <div className="text-xs text-gray-500">
              Created: {new Date(selected.created_at).toLocaleString()}
            </div>

            <section>
              <h4 className="text-sm font-medium text-gray-700 mb-1">System Prompt</h4>
              <PromptEditor value={selected.system_prompt} readOnly height="300px" />
            </section>

            {selected.tool_details && selected.tool_details.length > 0 && (
              <section>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Tools</h4>
                <div className="space-y-1">
                  {selected.tool_details.map((t, i) => (
                    <div key={i} className="border border-gray-200 rounded p-2 text-sm">
                      <span className="font-medium">{t.name}</span>
                      {t.usageGuidelines && (
                        <span className="text-gray-500 ml-2">— {t.usageGuidelines}</span>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {selected.widget_details && selected.widget_details.length > 0 && (
              <section>
                <h4 className="text-sm font-medium text-gray-700 mb-1">Widgets</h4>
                <div className="space-y-1">
                  {selected.widget_details.map((w, i) => (
                    <div key={i} className="border border-gray-200 rounded p-2 text-sm">
                      <span className="font-medium">{w.name}</span>
                      <span className="text-gray-500 ml-2">— {w.description}</span>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {selected.id !== agent.active_version_id && (
              <button
                onClick={() => handleSetActive(selected.id)}
                className="px-4 py-1.5 text-sm font-medium bg-green-600 text-white rounded hover:bg-green-700"
              >
                Set as Active
              </button>
            )}
          </div>
        ) : (
          <div className="text-gray-400 text-sm">Select a version to view details</div>
        )}
      </div>
    </div>
  )
}
