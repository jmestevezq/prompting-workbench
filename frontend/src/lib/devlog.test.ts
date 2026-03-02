import { describe, it, expect, beforeEach, vi } from 'vitest'
import { devLog, onDevLog, getDevLogHistory, clearDevLogHistory } from './devlog'

beforeEach(() => {
  clearDevLogHistory()
})

describe('devLog', () => {
  it('creates an entry with correct fields', () => {
    const entry = devLog('API_OUT', 'info', 'GET /api/agents')
    expect(entry.category).toBe('API_OUT')
    expect(entry.level).toBe('info')
    expect(entry.message).toBe('GET /api/agents')
    expect(entry.source).toBe('frontend')
    expect(entry.id).toBeTruthy()
    expect(entry.timestamp).toBeTruthy()
  })

  it('stores details when provided', () => {
    const entry = devLog('API_ERR', 'error', '404 /api/x', { status: 404 })
    expect(entry.details).toEqual({ status: 404 })
  })

  it('adds entry to buffer', () => {
    devLog('API_OUT', 'info', 'first')
    devLog('API_IN', 'info', 'second')
    const history = getDevLogHistory()
    expect(history).toHaveLength(2)
    expect(history[0].message).toBe('first')
    expect(history[1].message).toBe('second')
  })

  it('enforces buffer capacity of 500', () => {
    for (let i = 0; i < 510; i++) {
      devLog('API_OUT', 'debug', `msg-${i}`)
    }
    const history = getDevLogHistory()
    expect(history.length).toBeLessThanOrEqual(500)
    // Newest entries should be present
    expect(history[history.length - 1].message).toBe('msg-509')
  })

  it('notifies listeners on each emit', () => {
    const listener = vi.fn()
    const unsub = onDevLog(listener)
    devLog('WS_OUT', 'info', 'Connected')
    expect(listener).toHaveBeenCalledTimes(1)
    expect(listener.mock.calls[0][0].message).toBe('Connected')
    unsub()
  })

  it('stops notifying after unsubscribe', () => {
    const listener = vi.fn()
    const unsub = onDevLog(listener)
    unsub()
    devLog('WS_IN', 'info', 'message')
    expect(listener).not.toHaveBeenCalled()
  })

  it('notifies multiple listeners', () => {
    const l1 = vi.fn()
    const l2 = vi.fn()
    const u1 = onDevLog(l1)
    const u2 = onDevLog(l2)
    devLog('STATE', 'debug', 'state change')
    expect(l1).toHaveBeenCalledTimes(1)
    expect(l2).toHaveBeenCalledTimes(1)
    u1()
    u2()
  })
})

describe('getDevLogHistory', () => {
  it('returns a copy (mutation does not affect buffer)', () => {
    devLog('API_OUT', 'info', 'original')
    const history = getDevLogHistory()
    history.push({ id: 'x', timestamp: '', source: 'frontend', category: 'X', level: 'info', message: 'mutated' })
    expect(getDevLogHistory()).toHaveLength(1)
  })
})

describe('clearDevLogHistory', () => {
  it('empties the buffer', () => {
    devLog('API_OUT', 'info', 'a')
    devLog('API_IN', 'info', 'b')
    clearDevLogHistory()
    expect(getDevLogHistory()).toHaveLength(0)
  })
})
