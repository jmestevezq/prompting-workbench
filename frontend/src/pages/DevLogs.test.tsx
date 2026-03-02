import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import DevLogs from './DevLogs'
import { useDevLogStore } from '../store/devLogStore'
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

function renderPage() {
  return render(
    <MemoryRouter>
      <DevLogs />
    </MemoryRouter>,
  )
}

describe('DevLogs page', () => {
  it('renders the filter bar with source toggles', () => {
    renderPage()
    // 'all' appears in both source and level toggles — use getAllByText
    const allBtns = screen.getAllByText('all')
    expect(allBtns.length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('frontend')).toBeInTheDocument()
    expect(screen.getByText('backend')).toBeInTheDocument()
  })

  it('shows empty state when no entries', () => {
    renderPage()
    expect(screen.getByText('Waiting for log entries…')).toBeInTheDocument()
  })

  it('shows no-match state when entries exist but filters exclude all', () => {
    useDevLogStore.getState().addEntry(makeEntry({ source: 'frontend' }))
    renderPage()
    fireEvent.click(screen.getByText('backend'))
    expect(screen.getByText('No entries match the current filters.')).toBeInTheDocument()
  })

  it('renders log entries', () => {
    useDevLogStore.getState().addEntry(makeEntry({ message: 'GET /api/agents' }))
    useDevLogStore.getState().addEntry(makeEntry({ message: 'WS connected' }))
    renderPage()
    expect(screen.getByText('GET /api/agents')).toBeInTheDocument()
    expect(screen.getByText('WS connected')).toBeInTheDocument()
  })

  it('filters entries by source', () => {
    useDevLogStore.getState().addEntry(makeEntry({ source: 'frontend', message: 'frontend msg' }))
    useDevLogStore.getState().addEntry(makeEntry({ source: 'backend', message: 'backend msg' }))
    renderPage()

    fireEvent.click(screen.getByText('frontend'))
    expect(screen.getByText('frontend msg')).toBeInTheDocument()
    expect(screen.queryByText('backend msg')).not.toBeInTheDocument()
  })

  it('clears logs on Clear button click', () => {
    useDevLogStore.getState().addEntry(makeEntry({ message: 'to be cleared' }))
    renderPage()
    expect(screen.getByText('to be cleared')).toBeInTheDocument()

    fireEvent.click(screen.getByText('Clear'))
    expect(screen.queryByText('to be cleared')).not.toBeInTheDocument()
  })

  it('toggles pause state', () => {
    renderPage()
    const pauseBtn = screen.getByText('⏸ Pause')
    fireEvent.click(pauseBtn)
    expect(useDevLogStore.getState().isPaused).toBe(true)
    expect(screen.getByText('▶ Resume')).toBeInTheDocument()
  })

  it('shows SSE disconnected status by default', () => {
    renderPage()
    expect(screen.getByText('SSE Disconnected')).toBeInTheDocument()
  })

  it('shows SSE connected status when connected', () => {
    useDevLogStore.getState().setConnected(true)
    renderPage()
    expect(screen.getByText('SSE Connected')).toBeInTheDocument()
  })

  it('displays entry count in status bar', () => {
    useDevLogStore.getState().addEntry(makeEntry())
    useDevLogStore.getState().addEntry(makeEntry())
    renderPage()
    expect(screen.getByText('2 / 2 entries')).toBeInTheDocument()
  })

  it('filters entries by search text', () => {
    useDevLogStore.getState().addEntry(makeEntry({ message: 'fetch agents' }))
    useDevLogStore.getState().addEntry(makeEntry({ message: 'fetch profiles' }))
    renderPage()

    const searchInput = screen.getByPlaceholderText('Search...')
    fireEvent.change(searchInput, { target: { value: 'agents' } })

    expect(screen.getByText('fetch agents')).toBeInTheDocument()
    expect(screen.queryByText('fetch profiles')).not.toBeInTheDocument()
  })
})
