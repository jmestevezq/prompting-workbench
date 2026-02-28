import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { SettingsData } from '../api/types'

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [defaultModel, setDefaultModel] = useState('gemini-2.5-pro')
  const [concurrency, setConcurrency] = useState(5)
  const [timeout, setTimeout_] = useState(10)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.getSettings().then((s) => {
      setSettings(s)
      setDefaultModel(s.default_model)
      setConcurrency(s.batch_concurrency)
      setTimeout_(s.code_execution_timeout)
    })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      const updated = await api.updateSettings({
        gemini_api_key: apiKey || undefined,
        default_model: defaultModel,
        batch_concurrency: concurrency,
        code_execution_timeout: timeout,
      })
      setSettings(updated)
      setApiKey('')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-xl font-semibold mb-6">Settings</h1>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Gemini API Key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={settings?.has_api_key ? '••••••••  (configured)' : 'Enter API key'}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            {settings?.has_api_key ? 'API key is configured.' : 'No API key set.'}
          </p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Default Model</label>
          <select
            value={defaultModel}
            onChange={(e) => setDefaultModel(e.target.value)}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="gemini-2.5-pro">gemini-2.5-pro</option>
            <option value="gemini-2.5-flash">gemini-2.5-flash</option>
            <option value="gemini-2.0-flash">gemini-2.0-flash</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Batch Concurrency</label>
          <input
            type="number"
            value={concurrency}
            onChange={(e) => setConcurrency(Number(e.target.value))}
            min={1}
            max={20}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Code Execution Timeout (seconds)</label>
          <input
            type="number"
            value={timeout}
            onChange={(e) => setTimeout_(Number(e.target.value))}
            min={1}
            max={60}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
