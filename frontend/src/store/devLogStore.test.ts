import { describe, it, expect, beforeEach } from 'vitest'
import { useDevLogStore, selectFilteredEntries } from './devLogStore'
import type { DevLogEntry } from '../lib/devlog'

function makeEntry(overrides: Partial<DevLogEntry> = {}): DevLogEntry {
  return {
    id: Math.random().toString(),
    timestamp: new Date().toISOString(),
    source: 'frontend',
    category: 'API_OUT',
    level: 'info',
    message: 'test message',
    ...overrides,
  }
}

beforeEach(() => {
  useDevLogStore.setState({
    entries: [],
    filters: { source: 'all', level: 'all', category: '', search: '' },
    isPaused: false,
    isConnected: false,
  })
})

describe('addEntry', () => {
  it('appends an entry', () => {
    const entry = makeEntry({ message: 'hello' })
    useDevLogStore.getState().addEntry(entry)
    expect(useDevLogStore.getState().entries).toHaveLength(1)
    expect(useDevLogStore.getState().entries[0].message).toBe('hello')
  })

  it('enforces max 500 entries', () => {
    for (let i = 0; i < 510; i++) {
      useDevLogStore.getState().addEntry(makeEntry({ message: `msg-${i}` }))
    }
    expect(useDevLogStore.getState().entries.length).toBeLessThanOrEqual(500)
  })

  it('does not add entries when paused', () => {
    useDevLogStore.setState({ isPaused: true })
    useDevLogStore.getState().addEntry(makeEntry())
    expect(useDevLogStore.getState().entries).toHaveLength(0)
  })
})

describe('clearLogs', () => {
  it('removes all entries', () => {
    useDevLogStore.getState().addEntry(makeEntry())
    useDevLogStore.getState().addEntry(makeEntry())
    useDevLogStore.getState().clearLogs()
    expect(useDevLogStore.getState().entries).toHaveLength(0)
  })
})

describe('setFilter', () => {
  it('updates filter keys', () => {
    useDevLogStore.getState().setFilter('source', 'backend')
    expect(useDevLogStore.getState().filters.source).toBe('backend')

    useDevLogStore.getState().setFilter('level', 'error')
    expect(useDevLogStore.getState().filters.level).toBe('error')

    useDevLogStore.getState().setFilter('search', 'gemini')
    expect(useDevLogStore.getState().filters.search).toBe('gemini')
  })
})

describe('togglePause', () => {
  it('toggles isPaused', () => {
    expect(useDevLogStore.getState().isPaused).toBe(false)
    useDevLogStore.getState().togglePause()
    expect(useDevLogStore.getState().isPaused).toBe(true)
    useDevLogStore.getState().togglePause()
    expect(useDevLogStore.getState().isPaused).toBe(false)
  })
})

describe('setConnected', () => {
  it('updates connection status', () => {
    useDevLogStore.getState().setConnected(true)
    expect(useDevLogStore.getState().isConnected).toBe(true)
    useDevLogStore.getState().setConnected(false)
    expect(useDevLogStore.getState().isConnected).toBe(false)
  })
})

describe('selectFilteredEntries', () => {
  beforeEach(() => {
    const entries: DevLogEntry[] = [
      makeEntry({ id: '1', source: 'frontend', category: 'API_OUT', level: 'info', message: 'fetch agents' }),
      makeEntry({ id: '2', source: 'backend', category: 'REQ', level: 'info', message: 'GET /api/agents' }),
      makeEntry({ id: '3', source: 'frontend', category: 'WS_ERR', level: 'error', message: 'ws error' }),
      makeEntry({ id: '4', source: 'backend', category: 'GEMINI', level: 'debug', message: 'gemini call' }),
    ]
    useDevLogStore.setState({ entries })
  })

  it('returns all entries when no filters applied', () => {
    const state = useDevLogStore.getState()
    expect(selectFilteredEntries(state)).toHaveLength(4)
  })

  it('filters by source', () => {
    useDevLogStore.getState().setFilter('source', 'backend')
    const state = useDevLogStore.getState()
    const result = selectFilteredEntries(state)
    expect(result).toHaveLength(2)
    expect(result.every((e) => e.source === 'backend')).toBe(true)
  })

  it('filters by level', () => {
    useDevLogStore.getState().setFilter('level', 'error')
    const state = useDevLogStore.getState()
    const result = selectFilteredEntries(state)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('3')
  })

  it('filters by category', () => {
    useDevLogStore.getState().setFilter('category', 'GEMINI')
    const state = useDevLogStore.getState()
    const result = selectFilteredEntries(state)
    expect(result).toHaveLength(1)
    expect(result[0].id).toBe('4')
  })

  it('filters by search text (message)', () => {
    useDevLogStore.getState().setFilter('search', 'agents')
    const state = useDevLogStore.getState()
    const result = selectFilteredEntries(state)
    expect(result).toHaveLength(2)
  })

  it('filters by search text (category)', () => {
    useDevLogStore.getState().setFilter('search', 'ws')
    const state = useDevLogStore.getState()
    const result = selectFilteredEntries(state)
    expect(result.some((e) => e.id === '3')).toBe(true)
  })
})
