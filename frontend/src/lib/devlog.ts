/**
 * Frontend developer log module.
 *
 * Provides a module-level buffer and listener system for capturing
 * frontend events (API calls, WebSocket messages, state changes).
 * Backend events are merged in by the useBackendLogs hook.
 */

export interface DevLogEntry {
  id: string
  timestamp: string
  source: 'frontend' | 'backend'
  category: string   // API_OUT, API_IN, API_ERR, WS_OUT, WS_IN, WS_ERR, STATE
  level: 'info' | 'warn' | 'error' | 'debug'
  message: string
  details?: unknown
}

type Listener = (entry: DevLogEntry) => void

const MAX_BUFFER_SIZE = 500

let buffer: DevLogEntry[] = []
const listeners = new Set<Listener>()

let idCounter = 0
function nextId(): string {
  return `fe-${Date.now()}-${++idCounter}`
}

export function devLog(
  category: DevLogEntry['category'],
  level: DevLogEntry['level'],
  message: string,
  details?: unknown,
): DevLogEntry {
  const entry: DevLogEntry = {
    id: nextId(),
    timestamp: new Date().toISOString(),
    source: 'frontend',
    category,
    level,
    message,
    details,
  }

  buffer.push(entry)
  if (buffer.length > MAX_BUFFER_SIZE) {
    buffer = buffer.slice(buffer.length - MAX_BUFFER_SIZE)
  }

  listeners.forEach((fn) => fn(entry))
  return entry
}

export function onDevLog(listener: Listener): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function getDevLogHistory(): DevLogEntry[] {
  return [...buffer]
}

export function clearDevLogHistory(): void {
  buffer = []
}
