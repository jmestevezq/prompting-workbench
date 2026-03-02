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
    <div className="max-w-2xl mx-auto p-8">
      <div className="bg-white rounded-lg border border-slate-200 shadow-xs p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-6">Settings</h2>

        <div className="space-y-5">
          <div>
            <label className="block text-[13px] font-medium text-slate-700 mb-1.5">Gemini API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={settings?.has_api_key ? '••••••••  (configured)' : 'Enter API key'}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
            />
            <p className="text-xs text-slate-500 mt-1">
              {settings?.has_api_key ? 'API key is configured.' : 'No API key set.'}
            </p>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-slate-700 mb-1.5">Default Model</label>
            <select
              value={defaultModel}
              onChange={(e) => setDefaultModel(e.target.value)}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
            >
              <option value="gemini-2.5-pro">gemini-2.5-pro</option>
              <option value="gemini-2.5-flash">gemini-2.5-flash</option>
              <option value="gemini-2.0-flash">gemini-2.0-flash</option>
            </select>
          </div>

          <div>
            <label className="block text-[13px] font-medium text-slate-700 mb-1.5">Batch Concurrency</label>
            <input
              type="number"
              value={concurrency}
              onChange={(e) => setConcurrency(Number(e.target.value))}
              min={1}
              max={20}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
            />
          </div>

          <div>
            <label className="block text-[13px] font-medium text-slate-700 mb-1.5">Code Execution Timeout (seconds)</label>
            <input
              type="number"
              value={timeout}
              onChange={(e) => setTimeout_(Number(e.target.value))}
              min={1}
              max={60}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors"
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="bg-indigo-600 text-white px-4 py-2 rounded-md text-[13px] font-medium hover:bg-indigo-700 disabled:opacity-50 transition-all duration-150 active:scale-[0.98] shadow-xs"
          >
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </div>
    </div>
  )
}
