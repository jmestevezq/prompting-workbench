import { create } from 'zustand'
import type { Agent, Session, Fixture } from '../api/types'

interface AppState {
  // Active selections
  activeAgent: Agent | null
  activeSession: Session | null
  agents: Agent[]
  fixtures: Fixture[]

  // Actions
  setActiveAgent: (agent: Agent | null) => void
  setActiveSession: (session: Session | null) => void
  setAgents: (agents: Agent[]) => void
  setFixtures: (fixtures: Fixture[]) => void
}

export const useAppStore = create<AppState>((set) => ({
  activeAgent: null,
  activeSession: null,
  agents: [],
  fixtures: [],

  setActiveAgent: (agent) => set({ activeAgent: agent }),
  setActiveSession: (session) => set({ activeSession: session }),
  setAgents: (agents) => set({ agents }),
  setFixtures: (fixtures) => set({ fixtures }),
}))
