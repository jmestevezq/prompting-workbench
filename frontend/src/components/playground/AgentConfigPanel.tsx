import { useState, useEffect } from 'react'
import type { Agent, Fixture } from '../../api/types'
import PromptEditor from '../PromptEditor'
import JsonEditor from '../JsonEditor'

const todayStr = () => new Date().toISOString().split('T')[0]

function FixturePreview({
  fixture,
  label,
  onFixtureDataChange,
}: {
  fixture: Fixture
  label: string
  onFixtureDataChange: (fixtureId: string, data: unknown) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState('')

  const jsonStr = JSON.stringify(fixture.data, null, 2)

  const handleStartEdit = () => {
    setEditValue(jsonStr)
    setEditing(true)
    setExpanded(true)
  }

  const handleSave = () => {
    try {
      const parsed = JSON.parse(editValue)
      onFixtureDataChange(fixture.id, parsed)
      setEditing(false)
    } catch {
      // invalid JSON, don't save
    }
  }

  return (
    <div className="mt-2 border border-slate-200 rounded">
      <div
        className="flex items-center justify-between px-2 py-1.5 bg-slate-50 cursor-pointer"
        onClick={() => !editing && setExpanded(!expanded)}
      >
        <span className="text-xs text-slate-500 font-medium">{label}</span>
        <div className="flex items-center gap-1">
          {!editing && (
            <button
              onClick={(e) => { e.stopPropagation(); handleStartEdit() }}
              className="text-[10px] text-indigo-600 hover:text-indigo-700 px-1"
            >
              Edit
            </button>
          )}
          <span className="text-[10px] text-slate-400">{expanded ? '▼' : '▶'}</span>
        </div>
      </div>
      {expanded && (
        editing ? (
          <div>
            <JsonEditor
              value={editValue}
              onChange={setEditValue}
              height="180px"
            />
            <div className="flex gap-1 p-1.5 border-t border-slate-200 bg-slate-50">
              <button
                onClick={handleSave}
                className="text-xs px-2 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-700"
              >
                Save
              </button>
              <button
                onClick={() => setEditing(false)}
                className="text-xs px-2 py-1 rounded border border-slate-300 text-slate-700 hover:bg-slate-100"
              >
                Cancel
              </button>
            </div>
          </div>
        ) : (
          <pre className="text-xs p-2 max-h-48 overflow-auto">
            {jsonStr}
          </pre>
        )
      )}
    </div>
  )
}

interface AgentConfigPanelProps {
  agents: Agent[]
  activeAgent: Agent | null
  fixtures: Fixture[]
  selectedFixtureIds: string[]
  onAgentSelect: (agent: Agent) => void
  onAgentUpdate: (updates: Partial<Agent>) => void
  onFixtureSelect: (ids: string[]) => void
  onFixtureDataChange: (fixtureId: string, data: unknown) => void
  onSwapFixture: () => void
  onSaveVersion: (label: string) => void
  toolOverrides: Record<string, { data: unknown; active: boolean }>
  onSetToolOverride: (overrides: Record<string, { data: unknown; active: boolean }>) => void
  onClearToolOverrides: () => void
  sessionActive: boolean
}

export default function AgentConfigPanel({
  agents,
  activeAgent,
  fixtures,
  selectedFixtureIds,
  onAgentSelect,
  onAgentUpdate,
  onFixtureSelect,
  onFixtureDataChange,
  onSwapFixture,
  onSaveVersion,
  toolOverrides,
  onSetToolOverride,
  onClearToolOverrides,
  sessionActive,
}: AgentConfigPanelProps) {
  const [showPromptEditor, setShowPromptEditor] = useState(false)
  const [showOverrides, setShowOverrides] = useState(false)
  const [versionLabel, setVersionLabel] = useState('')
  const [showVersionSave, setShowVersionSave] = useState(false)
  const [overrideToolName, setOverrideToolName] = useState('')
  const [overrideJson, setOverrideJson] = useState('{}')

  const userProfiles = fixtures.filter((f) => f.type === 'user_profile')
  const transactions = fixtures.filter((f) => f.type === 'transactions')

  const selectedProfile = fixtures.find((f) => selectedFixtureIds.includes(f.id) && f.type === 'user_profile')
  const selectedTx = fixtures.find((f) => selectedFixtureIds.includes(f.id) && f.type === 'transactions')

  // Simulation date — synced from selected profile's currentDate field
  const [simulationDate, setSimulationDate] = useState(todayStr())
  useEffect(() => {
    if (selectedProfile) {
      const data = selectedProfile.data as Record<string, unknown>
      setSimulationDate((data?.currentDate as string) || todayStr())
    }
  }, [selectedProfile?.id, (selectedProfile?.data as Record<string, unknown>)?.currentDate])

  const handleSimulationDateChange = (newDate: string) => {
    setSimulationDate(newDate)
    if (!selectedProfile) return
    const data = { ...(selectedProfile.data as Record<string, unknown>), currentDate: newDate }
    onFixtureDataChange(selectedProfile.id, data)
  }

  const handleFixtureChange = (type: string, fixtureId: string) => {
    const otherIds = selectedFixtureIds.filter((id) => {
      const f = fixtures.find((fx) => fx.id === id)
      return f && f.type !== type
    })
    if (fixtureId) {
      onFixtureSelect([...otherIds, fixtureId])
    } else {
      onFixtureSelect(otherIds)
    }
  }

  const handleAddOverride = () => {
    if (!overrideToolName) return
    try {
      const data = JSON.parse(overrideJson)
      onSetToolOverride({
        ...toolOverrides,
        [overrideToolName]: { data, active: true },
      })
      setOverrideToolName('')
      setOverrideJson('{}')
    } catch {
      // Invalid JSON
    }
  }

  return (
    <div className="border-r border-slate-200 bg-white overflow-y-auto flex flex-col">
      <div className="p-3 border-b border-slate-200">
        <label className="block text-xs font-medium text-slate-500 mb-1">Agent</label>
        <select
          value={activeAgent?.id ?? ''}
          onChange={(e) => {
            const agent = agents.find((a) => a.id === e.target.value)
            if (agent) onAgentSelect(agent)
          }}
          className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">Select agent...</option>
          {agents.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      </div>

      {activeAgent && (
        <>
          {/* Model */}
          <div className="p-3 border-b border-slate-200">
            <label className="block text-xs font-medium text-slate-500 mb-1">Model</label>
            <select
              value={activeAgent.model}
              onChange={(e) => onAgentUpdate({ model: e.target.value })}
              className="w-full border border-slate-300 rounded px-2 py-1.5 text-sm"
            >
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-2.0-flash">gemini-2.0-flash</option>
            </select>
          </div>

          {/* System Prompt */}
          <div className="p-3 border-b border-slate-200">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-500">System Prompt</label>
              <button
                onClick={() => setShowPromptEditor(!showPromptEditor)}
                className="text-xs text-indigo-600 hover:text-indigo-700"
              >
                {showPromptEditor ? 'Collapse' : 'Expand'}
              </button>
            </div>
            {showPromptEditor ? (
              <PromptEditor
                value={activeAgent.system_prompt}
                onChange={(val) => onAgentUpdate({ system_prompt: val })}
                height="200px"
              />
            ) : (
              <div className="text-xs text-slate-600 bg-slate-50 rounded p-2 max-h-20 overflow-hidden">
                {activeAgent.system_prompt.slice(0, 150)}
                {activeAgent.system_prompt.length > 150 && '...'}
              </div>
            )}
            <div className="flex gap-1 mt-1">
              <button
                onClick={() => setShowVersionSave(true)}
                className="text-xs text-indigo-600 hover:text-indigo-700"
              >
                Save Version
              </button>
            </div>
            {showVersionSave && (
              <div className="flex gap-1 mt-1">
                <input
                  value={versionLabel}
                  onChange={(e) => setVersionLabel(e.target.value)}
                  placeholder="Label (e.g. v3-fixed)"
                  className="flex-1 border border-slate-300 rounded px-2 py-1 text-xs"
                />
                <button
                  onClick={() => {
                    onSaveVersion(versionLabel)
                    setVersionLabel('')
                    setShowVersionSave(false)
                  }}
                  className="bg-indigo-600 text-white px-2 py-1 rounded text-xs"
                >
                  Save
                </button>
              </div>
            )}
          </div>

          {/* Fixtures */}
          <div className="p-3 border-b border-slate-200">
            <label className="block text-xs font-medium text-slate-500 mb-1">Fixtures</label>
            <div className="space-y-2">
              <div>
                <label className="text-xs text-slate-400">User Profile</label>
                <select
                  value={selectedProfile?.id ?? ''}
                  onChange={(e) => handleFixtureChange('user_profile', e.target.value)}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
                >
                  <option value="">None</option>
                  {userProfiles.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400">Transactions</label>
                <select
                  value={selectedTx?.id ?? ''}
                  onChange={(e) => handleFixtureChange('transactions', e.target.value)}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
                >
                  <option value="">None</option>
                  {transactions.map((f) => (
                    <option key={f.id} value={f.id}>{f.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400">Simulation Date</label>
                <input
                  type="date"
                  value={simulationDate}
                  onChange={(e) => handleSimulationDateChange(e.target.value)}
                  disabled={!selectedProfile}
                  className="w-full border border-slate-300 rounded px-2 py-1 text-xs disabled:opacity-50 disabled:bg-slate-50"
                />
              </div>
            </div>
            {selectedProfile && (
              <FixturePreview
                fixture={selectedProfile}
                label="User Profile"
                onFixtureDataChange={onFixtureDataChange}
              />
            )}
            {selectedTx && (
              <FixturePreview
                fixture={selectedTx}
                label={`Transactions (${Array.isArray(selectedTx.data) ? selectedTx.data.length : 0})`}
                onFixtureDataChange={onFixtureDataChange}
              />
            )}
            {sessionActive && (
              <button
                onClick={onSwapFixture}
                className="mt-2 w-full bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs hover:bg-slate-200"
              >
                Swap Data
              </button>
            )}
          </div>

          {/* Tool Overrides */}
          <div className="p-3 flex-1">
            <div className="flex items-center justify-between mb-1">
              <label className="text-xs font-medium text-slate-500">Tool Overrides</label>
              <button
                onClick={() => setShowOverrides(!showOverrides)}
                className="text-xs text-indigo-600 hover:text-indigo-700"
              >
                {showOverrides ? 'Hide' : 'Show'}
              </button>
            </div>
            {Object.keys(toolOverrides).length > 0 && (
              <div className="space-y-1 mb-2">
                {Object.entries(toolOverrides).map(([name, override]) => (
                  <div key={name} className="flex items-center justify-between bg-yellow-50 rounded px-2 py-1 text-xs">
                    <span className={override.active ? 'text-yellow-700' : 'text-slate-400'}>
                      {name} {override.active ? '(active)' : '(inactive)'}
                    </span>
                  </div>
                ))}
                <button
                  onClick={onClearToolOverrides}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  Clear All
                </button>
              </div>
            )}
            {showOverrides && (
              <div className="space-y-1">
                <input
                  value={overrideToolName}
                  onChange={(e) => setOverrideToolName(e.target.value)}
                  placeholder="Tool name"
                  className="w-full border border-slate-300 rounded px-2 py-1 text-xs"
                />
                <JsonEditor
                  value={overrideJson}
                  onChange={setOverrideJson}
                  height="80px"
                />
                <button
                  onClick={handleAddOverride}
                  className="w-full bg-yellow-100 text-yellow-700 px-2 py-1 rounded text-xs hover:bg-yellow-200"
                >
                  Set Override
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
