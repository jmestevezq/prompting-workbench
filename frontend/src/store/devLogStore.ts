import { create } from 'zustand'
import type { DevLogEntry } from '../lib/devlog'

export interface DevLogFilters {
  source: 'all' | 'frontend' | 'backend'
  level: 'all' | 'info' | 'warn' | 'error' | 'debug'
  category: string  // '' = all
  search: string
}

interface DevLogState {
  entries: DevLogEntry[]
  filters: DevLogFilters
  isPaused: boolean
  isConnected: boolean
  isPanelOpen: boolean

  addEntry: (entry: DevLogEntry) => void
  clearLogs: () => void
  setFilter: <K extends keyof DevLogFilters>(key: K, value: DevLogFilters[K]) => void
  togglePause: () => void
  setConnected: (connected: boolean) => void
  togglePanel: () => void
  openPanel: () => void
}

const MAX_ENTRIES = 500

export const useDevLogStore = create<DevLogState>((set) => ({
  entries: [],
  filters: {
    source: 'all',
    level: 'all',
    category: '',
    search: '',
  },
  isPaused: false,
  isConnected: false,
  isPanelOpen: false,

  addEntry: (entry) =>
    set((state) => {
      if (state.isPaused) return state
      const next = [...state.entries, entry]
      return { entries: next.length > MAX_ENTRIES ? next.slice(next.length - MAX_ENTRIES) : next }
    }),

  clearLogs: () => set({ entries: [] }),

  setFilter: (key, value) =>
    set((state) => ({ filters: { ...state.filters, [key]: value } })),

  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),

  setConnected: (connected) => set({ isConnected: connected }),

  togglePanel: () => set((state) => ({ isPanelOpen: !state.isPanelOpen })),

  openPanel: () => set({ isPanelOpen: true }),
}))

/** Derive filtered entries from current store state. */
export function selectFilteredEntries(state: DevLogState): DevLogEntry[] {
  const { entries, filters } = state
  return entries.filter((e) => {
    if (filters.source !== 'all' && e.source !== filters.source) return false
    if (filters.level !== 'all' && e.level !== filters.level) return false
    if (filters.category && e.category !== filters.category) return false
    if (filters.search) {
      const q = filters.search.toLowerCase()
      if (!e.message.toLowerCase().includes(q) && !e.category.toLowerCase().includes(q)) {
        return false
      }
    }
    return true
  })
}
