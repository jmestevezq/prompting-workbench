import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import LogEntry from './LogEntry'
import type { DevLogEntry } from '../lib/devlog'

function makeEntry(overrides: Partial<DevLogEntry> = {}): DevLogEntry {
  return {
    id: '1',
    timestamp: '2024-01-01T10:00:00.000Z',
    source: 'backend',
    category: 'REQ',
    level: 'info',
    message: 'GET /api/agents',
    ...overrides,
  }
}

describe('LogEntry', () => {
  it('renders timestamp, category badge, and message', () => {
    render(<LogEntry entry={makeEntry()} />)
    expect(screen.getByText('GET /api/agents')).toBeInTheDocument()
    expect(screen.getByText('REQ')).toBeInTheDocument()
    // Timestamp formatting
    expect(screen.getByText(/\d{2}:\d{2}:\d{2}/)).toBeInTheDocument()
  })

  it('renders different category badges', () => {
    render(<LogEntry entry={makeEntry({ category: 'GEMINI', message: 'gemini call' })} />)
    expect(screen.getByText('GEMINI')).toBeInTheDocument()
  })

  it('is not interactive when no details', () => {
    const { container } = render(<LogEntry entry={makeEntry({ details: undefined })} />)
    const el = container.firstElementChild as HTMLElement
    // No role=button when no details
    expect(el.getAttribute('role')).toBeNull()
  })

  it('expands to show details JSON on click when details present', () => {
    const entry = makeEntry({ details: { tool: 'execute_code', args: {} } })
    render(<LogEntry entry={entry} />)

    // Click to expand
    const container = screen.getByRole('button')
    fireEvent.click(container)

    expect(screen.getByText(/"tool":/)).toBeInTheDocument()
  })

  it('collapses on second click', () => {
    const entry = makeEntry({ details: { key: 'value' } })
    render(<LogEntry entry={entry} />)

    const btn = screen.getByRole('button')
    fireEvent.click(btn)
    expect(screen.getByText(/"key":/)).toBeInTheDocument()

    fireEvent.click(btn)
    expect(screen.queryByText(/"key":/)).not.toBeInTheDocument()
  })

  it('renders error level entry', () => {
    render(<LogEntry entry={makeEntry({ level: 'error', category: 'ERR', message: 'Something broke' })} />)
    expect(screen.getByText('Something broke')).toBeInTheDocument()
  })
})
