import { useEffect } from 'react'
import { useDevLogStore } from '../store/devLogStore'
import type { DevLogEntry } from '../lib/devlog'

/**
 * Connects to the backend SSE log stream and feeds entries into the devlog store.
 * Should be mounted once at the Layout level so logs are captured from app start.
 */
export function useBackendLogs() {
  const addEntry = useDevLogStore((s) => s.addEntry)
  const setConnected = useDevLogStore((s) => s.setConnected)

  useEffect(() => {
    let es: EventSource | null = null
    let closed = false

    function connect() {
      if (closed) return

      es = new EventSource('/api/devlogs/stream')

      es.onopen = () => {
        setConnected(true)
      }

      es.onmessage = (event) => {
        try {
          const raw = JSON.parse(event.data) as {
            id: string
            timestamp: string
            category: string
            level: string
            message: string
            details?: unknown
          }
          const entry: DevLogEntry = {
            id: raw.id,
            timestamp: raw.timestamp,
            source: 'backend',
            category: raw.category,
            level: raw.level as DevLogEntry['level'],
            message: raw.message,
            details: raw.details,
          }
          addEntry(entry)
        } catch {
          // Ignore malformed SSE messages
        }
      }

      es.onerror = () => {
        setConnected(false)
        es?.close()
        // Reconnect after 3 seconds
        if (!closed) {
          setTimeout(connect, 3000)
        }
      }
    }

    connect()

    return () => {
      closed = true
      es?.close()
      setConnected(false)
    }
  }, [addEntry, setConnected])
}
