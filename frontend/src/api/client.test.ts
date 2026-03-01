/**
 * Tests for the REST API client.
 *
 * Focus: URL construction, HTTP methods, request bodies, error handling,
 *        204 responses, and query string building.
 */

import { api } from './client'

function mockResponse(body: unknown, status = 200) {
  const ok = status >= 200 && status < 300
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(typeof body === 'string' ? body : JSON.stringify(body)),
  }))
}

function lastCall() {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>
  return fetchMock.mock.calls[fetchMock.mock.calls.length - 1]
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('request mechanics', () => {
  it('sends Content-Type: application/json header', async () => {
    mockResponse([])
    await api.listAgents()
    expect(lastCall()[1]).toMatchObject({ headers: { 'Content-Type': 'application/json' } })
  })

  it('throws on non-ok response with status and body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve('Not found'),
    }))
    await expect(api.getAgent('bad-id')).rejects.toThrow('404: Not found')
  })

  it('returns undefined for 204 No Content responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 204,
      json: vi.fn(),
    }))
    const result = await api.deleteAgent('x')
    expect(result).toBeUndefined()
  })

  it('returns parsed JSON for 200 responses', async () => {
    const agent = { id: '1', name: 'Bot', system_prompt: 'Hi', model: 'gemini', tool_definitions: [], created_at: '', updated_at: '' }
    mockResponse(agent)
    const result = await api.getAgent('1')
    expect(result).toEqual(agent)
  })
})

describe('agents', () => {
  it('listAgents calls GET /api/agents', async () => {
    mockResponse([])
    await api.listAgents()
    expect(lastCall()[0]).toBe('/api/agents')
    expect(lastCall()[1]?.method).toBeUndefined() // defaults to GET
  })

  it('getAgent calls GET /api/agents/:id', async () => {
    mockResponse({})
    await api.getAgent('agent-42')
    expect(lastCall()[0]).toBe('/api/agents/agent-42')
  })

  it('createAgent calls POST /api/agents with JSON body', async () => {
    mockResponse({})
    await api.createAgent({ name: 'Bot', system_prompt: 'Be helpful' })
    expect(lastCall()[0]).toBe('/api/agents')
    expect(lastCall()[1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({ name: 'Bot', system_prompt: 'Be helpful' }),
    })
  })

  it('updateAgent calls PUT /api/agents/:id', async () => {
    mockResponse({})
    await api.updateAgent('a1', { name: 'New Name' })
    expect(lastCall()[0]).toBe('/api/agents/a1')
    expect(lastCall()[1]).toMatchObject({ method: 'PUT' })
  })

  it('deleteAgent calls DELETE /api/agents/:id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204, json: vi.fn() }))
    await api.deleteAgent('a1')
    expect(lastCall()[0]).toBe('/api/agents/a1')
    expect(lastCall()[1]).toMatchObject({ method: 'DELETE' })
  })

  it('listVersions calls GET /api/agents/:id/versions', async () => {
    mockResponse([])
    await api.listVersions('a1')
    expect(lastCall()[0]).toBe('/api/agents/a1/versions')
  })

  it('createVersion calls POST /api/agents/:id/versions', async () => {
    mockResponse({})
    await api.createVersion('a1', 'v1.0')
    expect(lastCall()[0]).toBe('/api/agents/a1/versions')
    expect(lastCall()[1]).toMatchObject({ method: 'POST', body: JSON.stringify({ label: 'v1.0' }) })
  })
})

describe('fixtures', () => {
  it('listFixtures calls GET /api/fixtures', async () => {
    mockResponse([])
    await api.listFixtures()
    expect(lastCall()[0]).toBe('/api/fixtures')
  })

  it('createFixture calls POST /api/fixtures', async () => {
    mockResponse({})
    await api.createFixture({ name: 'Fixture A', type: 'transactions', data: [] })
    expect(lastCall()[1]).toMatchObject({ method: 'POST' })
    const body = JSON.parse(lastCall()[1].body)
    expect(body.name).toBe('Fixture A')
  })

  it('deleteFixture calls DELETE /api/fixtures/:id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204, json: vi.fn() }))
    await api.deleteFixture('f1')
    expect(lastCall()[0]).toBe('/api/fixtures/f1')
    expect(lastCall()[1]).toMatchObject({ method: 'DELETE' })
  })
})

describe('sessions', () => {
  it('listSessions calls GET /api/sessions', async () => {
    mockResponse([])
    await api.listSessions()
    expect(lastCall()[0]).toBe('/api/sessions')
  })

  it('listTurns defaults to active_only=true', async () => {
    mockResponse([])
    await api.listTurns('s1')
    expect(lastCall()[0]).toBe('/api/sessions/s1/turns?active_only=true')
  })

  it('listTurns respects active_only=false', async () => {
    mockResponse([])
    await api.listTurns('s1', false)
    expect(lastCall()[0]).toBe('/api/sessions/s1/turns?active_only=false')
  })
})

describe('transcripts', () => {
  it('listTranscripts with no filters calls /api/transcripts', async () => {
    mockResponse([])
    await api.listTranscripts()
    expect(lastCall()[0]).toBe('/api/transcripts')
  })

  it('listTranscripts with tag filter adds ?tag= query string', async () => {
    mockResponse([])
    await api.listTranscripts('safety')
    expect(lastCall()[0]).toBe('/api/transcripts?tag=safety')
  })

  it('listTranscripts with source filter adds ?source= query string', async () => {
    mockResponse([])
    await api.listTranscripts(undefined, 'generated')
    expect(lastCall()[0]).toBe('/api/transcripts?source=generated')
  })

  it('listTranscripts with both filters includes both params', async () => {
    mockResponse([])
    await api.listTranscripts('safety', 'manual')
    const url = lastCall()[0] as string
    expect(url).toContain('tag=safety')
    expect(url).toContain('source=manual')
  })

  it('importTranscripts wraps array under transcripts key', async () => {
    mockResponse([])
    const items = [{ content: 'Hi', labels: {}, source: 'imported' }]
    await api.importTranscripts(items as Parameters<typeof api.importTranscripts>[0])
    const body = JSON.parse(lastCall()[1].body)
    expect(body).toHaveProperty('transcripts')
    expect(body.transcripts).toEqual(items)
  })

  it('deleteTranscript calls DELETE /api/transcripts/:id', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204, json: vi.fn() }))
    await api.deleteTranscript('t1')
    expect(lastCall()[0]).toBe('/api/transcripts/t1')
    expect(lastCall()[1]).toMatchObject({ method: 'DELETE' })
  })
})

describe('autoraters', () => {
  it('listAutoraters calls GET /api/autoraters', async () => {
    mockResponse([])
    await api.listAutoraters()
    expect(lastCall()[0]).toBe('/api/autoraters')
  })

  it('createAutorater calls POST /api/autoraters', async () => {
    mockResponse({})
    await api.createAutorater({ name: 'Rater', prompt: '{{transcript}}' })
    expect(lastCall()[1]).toMatchObject({ method: 'POST' })
  })
})

describe('eval runs', () => {
  it('startEvalRun omits eval_tags when empty array', async () => {
    mockResponse({ id: 'r1', status: 'running', transcript_ids: [], autorater_id: 'a1', created_at: '' })
    await api.startEvalRun('a1', ['t1'], [])
    const body = JSON.parse(lastCall()[1].body)
    expect(body.eval_tags).toBeUndefined()
  })

  it('startEvalRun includes eval_tags when non-empty', async () => {
    mockResponse({ id: 'r1', status: 'running', transcript_ids: [], autorater_id: 'a1', created_at: '' })
    await api.startEvalRun('a1', ['t1'], ['safety'])
    const body = JSON.parse(lastCall()[1].body)
    expect(body.eval_tags).toEqual(['safety'])
  })

  it('startEvalRun omits eval_tags when undefined', async () => {
    mockResponse({ id: 'r1', status: 'running', transcript_ids: [], autorater_id: 'a1', created_at: '' })
    await api.startEvalRun('a1', ['t1'])
    const body = JSON.parse(lastCall()[1].body)
    expect(body.eval_tags).toBeUndefined()
  })

  it('getEvalResults calls GET /api/eval/runs/:id/results', async () => {
    mockResponse([])
    await api.getEvalResults('run-1')
    expect(lastCall()[0]).toBe('/api/eval/runs/run-1/results')
  })

  it('diffEvalRuns calls GET /api/eval/runs/:id/diff/:otherId', async () => {
    mockResponse({})
    await api.diffEvalRuns('r1', 'r2')
    expect(lastCall()[0]).toBe('/api/eval/runs/r1/diff/r2')
  })
})

describe('golden sets', () => {
  it('listGoldenSets calls GET /api/golden-sets', async () => {
    mockResponse([])
    await api.listGoldenSets()
    expect(lastCall()[0]).toBe('/api/golden-sets')
  })

  it('importGoldenSets wraps items under items key', async () => {
    mockResponse([])
    const items = [{ set_name: 'my-set', input_transactions: [], expected_output: [] }]
    await api.importGoldenSets(items)
    const body = JSON.parse(lastCall()[1].body)
    expect(body).toHaveProperty('items')
    expect(body.items).toEqual(items)
  })
})

describe('classification', () => {
  it('startClassificationRun sends prompt_id and golden_set_name', async () => {
    mockResponse({ id: 'cr1', status: 'running', prompt_id: 'p1', created_at: '' })
    await api.startClassificationRun('p1', 'my-golden-set')
    const body = JSON.parse(lastCall()[1].body)
    expect(body.prompt_id).toBe('p1')
    expect(body.golden_set_name).toBe('my-golden-set')
  })

  it('getClassificationResults calls GET /api/classification/runs/:id/results', async () => {
    mockResponse([])
    await api.getClassificationResults('cr1')
    expect(lastCall()[0]).toBe('/api/classification/runs/cr1/results')
  })
})

describe('settings', () => {
  it('getSettings calls GET /api/settings', async () => {
    mockResponse({ has_api_key: true, default_model: 'gemini-2.5-pro', batch_concurrency: 5, code_execution_timeout: 10 })
    await api.getSettings()
    expect(lastCall()[0]).toBe('/api/settings')
  })

  it('updateSettings calls PUT /api/settings', async () => {
    mockResponse({ has_api_key: true, default_model: 'gemini-2.5-pro', batch_concurrency: 5, code_execution_timeout: 10 })
    await api.updateSettings({ default_model: 'gemini-2.0-pro' })
    expect(lastCall()[1]).toMatchObject({ method: 'PUT' })
    const body = JSON.parse(lastCall()[1].body)
    expect(body.default_model).toBe('gemini-2.0-pro')
  })
})
