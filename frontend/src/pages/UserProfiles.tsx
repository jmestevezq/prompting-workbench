import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { Fixture } from '../api/types'
import DataTable from '../components/DataTable'
import JsonEditor from '../components/JsonEditor'

const todayStr = () => new Date().toISOString().split('T')[0]

const defaultTxPrompt = () => {
  const end = new Date()
  const start = new Date()
  start.setMonth(start.getMonth() - 3)
  const fmt = (d: Date) => d.toISOString().split('T')[0]
  return `Generate transactions between ${fmt(start)} and ${fmt(end)} for several categories, at least 20 per week, 4 different categories, include salary, flat rent transactions and P2P. Rupee transactions only.`
}

export default function UserProfiles() {
  const [profiles, setProfiles] = useState<Fixture[]>([])
  const [transactions, setTransactions] = useState<Fixture[]>([])
  const [selected, setSelected] = useState<Fixture | null>(null)
  const [selectedTx, setSelectedTx] = useState<Fixture | null>(null)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [simulationDate, setSimulationDate] = useState(todayStr())
  const [jsonData, setJsonData] = useState('{}')
  const [txJsonData, setTxJsonData] = useState('[]')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [generatingProfile, setGeneratingProfile] = useState(false)
  const [txPrompt, setTxPrompt] = useState('')
  const [generatingTx, setGeneratingTx] = useState(false)

  const loadFixtures = async () => {
    const fixtures = await api.listFixtures()
    setProfiles(fixtures.filter((f) => f.type === 'user_profile'))
    setTransactions(fixtures.filter((f) => f.type === 'transactions'))
  }

  useEffect(() => {
    loadFixtures()
  }, [])

  const handleSelect = (p: Fixture) => {
    setSelected(p)
    setCreating(false)
    setName(p.name)
    setError('')
    setTxPrompt('')

    // Extract currentDate from profile data, default to today
    const data = p.data as Record<string, unknown>
    const dateVal = (data?.currentDate as string) || todayStr()
    setSimulationDate(dateVal)

    // Remove currentDate from JSON display — it's managed by the date picker
    const { currentDate: _, ...rest } = data || {}
    setJsonData(JSON.stringify(rest, null, 2))

    // Auto-select the first transactions fixture (1:1 for now)
    const tx = transactions.length > 0 ? transactions[0] : null
    setSelectedTx(tx)
    setTxJsonData(tx ? JSON.stringify(tx.data, null, 2) : '[]')
  }

  const handleNew = async () => {
    setSelected(null)
    setCreating(true)
    setError('')
    setGeneratingProfile(true)
    setName('Generating...')
    setSimulationDate(todayStr())
    setJsonData('{}')
    setTxJsonData('[]')
    setSelectedTx(null)
    setTxPrompt(defaultTxPrompt())

    try {
      const result = await api.generateProfile()
      setName(result.name)
      const data = result.data as Record<string, unknown>
      const { currentDate: _, ...rest } = data || {}
      setJsonData(JSON.stringify(rest, null, 2))
    } catch (e) {
      setName('')
      setJsonData('{}')
      setError(e instanceof Error ? `Profile generation failed: ${e.message}` : 'Profile generation failed')
    } finally {
      setGeneratingProfile(false)
    }
  }

  const handleGenerateTx = async () => {
    setError('')
    setGeneratingTx(true)
    try {
      const end = new Date()
      const start = new Date()
      start.setMonth(start.getMonth() - 3)
      const fmt = (d: Date) => d.toISOString().split('T')[0]

      let profileData: unknown = undefined
      try {
        profileData = JSON.parse(jsonData)
      } catch {
        // profile context is optional
      }

      const result = await api.generateTransactions({
        prompt: txPrompt,
        start_date: fmt(start),
        end_date: fmt(end),
        profile_data: profileData,
      })
      setTxJsonData(JSON.stringify(result.transactions, null, 2))
    } catch (e) {
      setError(e instanceof Error ? `Transaction generation failed: ${e.message}` : 'Transaction generation failed')
    } finally {
      setGeneratingTx(false)
    }
  }

  const handleSave = async () => {
    setError('')
    let parsed: unknown
    try {
      parsed = JSON.parse(jsonData)
    } catch {
      setError('Invalid JSON in profile data')
      return
    }
    // Inject simulation date into profile data
    if (typeof parsed === 'object' && parsed !== null) {
      (parsed as Record<string, unknown>).currentDate = simulationDate
    }
    let parsedTx: unknown
    try {
      parsedTx = JSON.parse(txJsonData)
    } catch {
      setError('Invalid JSON in transactions data')
      return
    }
    setSaving(true)
    try {
      if (creating) {
        const created = await api.createFixture({ name, type: 'user_profile', data: parsed })
        // Create transactions fixture if none exists
        if (!selectedTx) {
          await api.createFixture({ name: `${name} Transactions`, type: 'transactions', data: parsedTx })
        } else {
          await api.updateFixture(selectedTx.id, { data: parsedTx })
        }
        await loadFixtures()
        setSelected(created)
        setCreating(false)
      } else if (selected) {
        const updated = await api.updateFixture(selected.id, { name, data: parsed })
        // Save transactions if we have one
        if (selectedTx) {
          await api.updateFixture(selectedTx.id, { data: parsedTx })
        }
        await loadFixtures()
        setSelected(updated)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selected) return
    await api.deleteFixture(selected.id)
    setSelected(null)
    setSelectedTx(null)
    await loadFixtures()
  }

  const columns = [
    { key: 'name', header: 'Name' },
    {
      key: 'created_at',
      header: 'Created',
      render: (r: Fixture) => new Date(r.created_at).toLocaleDateString(),
    },
  ]

  return (
    <div className="h-full flex">
      {/* Left panel — profile list */}
      <div className="w-80 border-r border-slate-200 flex flex-col bg-white">
        <div className="p-3 border-b border-slate-200 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-700">User Profiles</h2>
          <button
            onClick={handleNew}
            disabled={generatingProfile}
            className="px-3 py-1 text-xs font-medium bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {generatingProfile ? 'Generating...' : 'New Profile'}
          </button>
        </div>
        <div className="flex-1 overflow-auto">
          <DataTable
            columns={columns}
            data={profiles}
            onRowClick={handleSelect}
            emptyMessage="No user profiles"
          />
        </div>
      </div>

      {/* Right panel — detail / create */}
      <div className="flex-1 p-6 overflow-auto">
        {!selected && !creating ? (
          <div className="text-slate-400 text-sm">Select a profile or create a new one</div>
        ) : (
          <div className="max-w-4xl space-y-4">
            {generatingProfile && (
              <div className="flex items-center gap-3 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
                <div className="h-5 w-5 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-indigo-700 font-medium">Generating random user profile with Gemini...</span>
              </div>
            )}

            <div className="flex gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full border border-slate-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                  placeholder="Profile name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Simulation Date</label>
                <input
                  type="date"
                  value={simulationDate}
                  onChange={(e) => setSimulationDate(e.target.value)}
                  className="border border-slate-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Profile Data (JSON)</label>
              <JsonEditor value={jsonData} onChange={setJsonData} height="300px" />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Transactions (JSON)
                {!selectedTx && !creating && (
                  <span className="ml-2 text-xs text-slate-400">No transactions fixture — will be created on save</span>
                )}
              </label>
              <div className="flex gap-4">
                {/* Left: transaction JSON editor */}
                <div className="flex-1">
                  <JsonEditor value={txJsonData} onChange={setTxJsonData} height="300px" />
                </div>

                {/* Right: generate transactions panel */}
                {creating && (
                  <div className="w-80 flex flex-col border border-slate-200 rounded-lg p-3 bg-slate-50">
                    <h3 className="text-sm font-semibold text-slate-700 mb-2">Generate Transactions</h3>
                    <textarea
                      value={txPrompt}
                      onChange={(e) => setTxPrompt(e.target.value)}
                      rows={8}
                      className="w-full border border-slate-300 rounded px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500 resize-none mb-3"
                      placeholder="Describe what transactions to generate..."
                    />
                    <button
                      onClick={handleGenerateTx}
                      disabled={generatingTx || !txPrompt.trim()}
                      className="w-full px-3 py-2 text-sm font-medium bg-emerald-600 text-white rounded hover:bg-emerald-700 disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {generatingTx ? (
                        <>
                          <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Generating...
                        </>
                      ) : (
                        'Generate'
                      )}
                    </button>
                    {generatingTx && (
                      <p className="mt-2 text-xs text-slate-500 text-center">
                        This may take 15-30 seconds...
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {error && <div className="text-rose-600 text-sm">{error}</div>}

            <div className="flex gap-2">
              <button
                onClick={handleSave}
                disabled={saving || !name.trim()}
                className="px-4 py-1.5 text-sm font-medium bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                {saving ? 'Saving...' : creating ? 'Create' : 'Save'}
              </button>
              {selected && !creating && (
                <button
                  onClick={handleDelete}
                  className="px-4 py-1.5 text-sm font-medium bg-rose-600 text-white rounded hover:bg-rose-700"
                >
                  Delete
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
