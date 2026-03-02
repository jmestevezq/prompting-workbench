import type {
  Agent, AgentCreate, AgentUpdate,
  Fixture, FixtureCreate,
  GenerateTransactionsRequest, GenerateProfileResponse, GenerateTransactionsResponse,
  Session, SessionCreate, Turn,
  Transcript, TranscriptCreate,
  Autorater, AutoraterCreate,
  EvalRun, EvalResult,
  GoldenTransaction, GoldenTransactionCreate,
  ClassificationPrompt, ClassificationPromptCreate,
  ClassificationRun, ClassificationResult,
  SettingsData, SettingsUpdate,
  PromptVersion,
  AgentVersion, AgentVersionCreate, AgentImportResponse, AgentTemplateResponse,
} from './types'
import { devLog } from '../lib/devlog'

const BASE = '/api'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const method = options?.method ?? 'GET'
  devLog('API_OUT', 'info', `${method} ${path}`)

  let res: Response
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    })
  } catch (err) {
    devLog('API_ERR', 'error', `${method} ${path} — network error`, { error: String(err) })
    throw err
  }

  if (!res.ok) {
    const text = await res.text()
    devLog('API_ERR', 'warn', `${res.status} ${method} ${path}`, { body: text.slice(0, 200) })
    throw new Error(`${res.status}: ${text}`)
  }

  devLog('API_IN', 'info', `${res.status} ${method} ${path}`)

  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  // Agents
  listAgents: () => request<Agent[]>('/agents'),
  createAgent: (data: AgentCreate) => request<Agent>('/agents', { method: 'POST', body: JSON.stringify(data) }),
  getAgent: (id: string) => request<Agent>(`/agents/${id}`),
  updateAgent: (id: string, data: AgentUpdate) => request<Agent>(`/agents/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteAgent: (id: string) => request<void>(`/agents/${id}`, { method: 'DELETE' }),
  listVersions: (agentId: string) => request<PromptVersion[]>(`/agents/${agentId}/versions`),
  createVersion: (agentId: string, label?: string) => request<PromptVersion>(`/agents/${agentId}/versions`, { method: 'POST', body: JSON.stringify({ label }) }),
  updateVersionLabel: (agentId: string, versionId: string, label: string) =>
    request<PromptVersion>(`/agents/${agentId}/versions/${versionId}/label`, { method: 'POST', body: JSON.stringify({ label }) }),

  // Agent Versions (file-based template system)
  listAgentVersions: (agentId: string) => request<AgentVersion[]>(`/agents/${agentId}/agent-versions`),
  createAgentVersion: (agentId: string, data: AgentVersionCreate) =>
    request<AgentVersion>(`/agents/${agentId}/agent-versions`, { method: 'POST', body: JSON.stringify(data) }),
  setActiveVersion: (agentId: string, versionId: string) =>
    request<void>(`/agents/${agentId}/active-version?version_id=${versionId}`, { method: 'PUT' }),
  getAgentTemplate: (agentId: string) => request<AgentTemplateResponse>(`/agents/${agentId}/template`),
  importAgent: (folderName: string) => request<AgentImportResponse>(`/agents/import/${folderName}`, { method: 'POST' }),
  listAgentFolders: () => request<{folders: string[]}>('/agents/folders/available').then(r => r.folders),

  // Fixtures
  listFixtures: () => request<Fixture[]>('/fixtures'),
  createFixture: (data: FixtureCreate) => request<Fixture>('/fixtures', { method: 'POST', body: JSON.stringify(data) }),
  getFixture: (id: string) => request<Fixture>(`/fixtures/${id}`),
  updateFixture: (id: string, data: Partial<FixtureCreate>) => request<Fixture>(`/fixtures/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteFixture: (id: string) => request<void>(`/fixtures/${id}`, { method: 'DELETE' }),
  generateProfile: () => request<GenerateProfileResponse>('/fixtures/generate-profile', { method: 'POST' }),
  generateTransactions: (data: GenerateTransactionsRequest) =>
    request<GenerateTransactionsResponse>('/fixtures/generate-transactions', { method: 'POST', body: JSON.stringify(data) }),

  // Sessions
  listSessions: () => request<Session[]>('/sessions'),
  createSession: (data: SessionCreate) => request<Session>('/sessions', { method: 'POST', body: JSON.stringify(data) }),
  getSession: (id: string) => request<Session>(`/sessions/${id}`),
  listTurns: (sessionId: string, activeOnly = true) => request<Turn[]>(`/sessions/${sessionId}/turns?active_only=${activeOnly}`),

  // Transcripts
  listTranscripts: (tag?: string, source?: string) => {
    const params = new URLSearchParams()
    if (tag) params.set('tag', tag)
    if (source) params.set('source', source)
    const qs = params.toString()
    return request<Transcript[]>(`/transcripts${qs ? `?${qs}` : ''}`)
  },
  createTranscript: (data: TranscriptCreate) => request<Transcript>('/transcripts', { method: 'POST', body: JSON.stringify(data) }),
  getTranscript: (id: string) => request<Transcript>(`/transcripts/${id}`),
  updateTranscript: (id: string, data: Partial<TranscriptCreate>) => request<Transcript>(`/transcripts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteTranscript: (id: string) => request<void>(`/transcripts/${id}`, { method: 'DELETE' }),
  importTranscripts: (transcripts: TranscriptCreate[]) => request<Transcript[]>('/transcripts/import', { method: 'POST', body: JSON.stringify({ transcripts }) }),

  // Autoraters
  listAutoraters: () => request<Autorater[]>('/autoraters'),
  createAutorater: (data: AutoraterCreate) => request<Autorater>('/autoraters', { method: 'POST', body: JSON.stringify(data) }),
  getAutorater: (id: string) => request<Autorater>(`/autoraters/${id}`),
  updateAutorater: (id: string, data: Partial<AutoraterCreate>) => request<Autorater>(`/autoraters/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Eval Runs
  startEvalRun: (autorater_id: string, transcript_ids: string[], eval_tags?: string[]) =>
    request<EvalRun>('/eval/run', { method: 'POST', body: JSON.stringify({
      autorater_id, transcript_ids,
      eval_tags: eval_tags?.length ? eval_tags : undefined,
    }) }),
  listEvalRuns: () => request<EvalRun[]>('/eval/runs'),
  getEvalRun: (id: string) => request<EvalRun>(`/eval/runs/${id}`),
  getEvalResults: (runId: string) => request<EvalResult[]>(`/eval/runs/${runId}/results`),
  diffEvalRuns: (runId: string, otherId: string) => request<unknown>(`/eval/runs/${runId}/diff/${otherId}`),

  // Transcript Generation
  generateTranscripts: (data: { reference_transcript_ids: string[]; prompt: string; count?: number; model?: string; agent_id?: string; auto_save?: boolean }) =>
    request<{ generated: { content: string; tags: string[] }[]; saved_ids: string[] }>('/generate/transcripts', { method: 'POST', body: JSON.stringify(data) }),

  // Golden Sets
  listGoldenSets: () => request<GoldenTransaction[]>('/golden-sets'),
  createGoldenSet: (data: GoldenTransactionCreate) => request<GoldenTransaction>('/golden-sets', { method: 'POST', body: JSON.stringify(data) }),
  updateGoldenSet: (id: string, data: Partial<GoldenTransactionCreate>) => request<GoldenTransaction>(`/golden-sets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  importGoldenSets: (items: GoldenTransactionCreate[]) => request<GoldenTransaction[]>('/golden-sets/import', { method: 'POST', body: JSON.stringify({ items }) }),

  // Classification Prompts
  listClassificationPrompts: () => request<ClassificationPrompt[]>('/classification/prompts'),
  createClassificationPrompt: (data: ClassificationPromptCreate) => request<ClassificationPrompt>('/classification/prompts', { method: 'POST', body: JSON.stringify(data) }),
  updateClassificationPrompt: (id: string, data: Partial<ClassificationPromptCreate>) =>
    request<ClassificationPrompt>(`/classification/prompts/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  // Classification Runs
  startClassificationRun: (prompt_id: string, golden_set_name: string) =>
    request<ClassificationRun>('/classification/run', { method: 'POST', body: JSON.stringify({ prompt_id, golden_set_name }) }),
  listClassificationRuns: () => request<ClassificationRun[]>('/classification/runs'),
  getClassificationRun: (id: string) => request<ClassificationRun>(`/classification/runs/${id}`),
  getClassificationResults: (runId: string) => request<ClassificationResult[]>(`/classification/runs/${runId}/results`),

  // Settings
  getSettings: () => request<SettingsData>('/settings'),
  updateSettings: (data: SettingsUpdate) => request<SettingsData>('/settings', { method: 'PUT', body: JSON.stringify(data) }),
}
