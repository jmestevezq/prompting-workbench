import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '../api/client'
import { ChatWebSocket } from '../api/websocket'
import type { Agent, Session, Turn, WsServerMessage, ToolCall } from '../api/types'
import { useAppStore } from '../store'
import AgentConfigPanel from '../components/playground/AgentConfigPanel'
import ChatPanel from '../components/playground/ChatPanel'
import DebugPanel from '../components/playground/DebugPanel'

interface ChatMessage {
  id?: string
  role: 'user' | 'agent' | 'tool_call' | 'tool_response' | 'system'
  content: string
  toolCall?: ToolCall
  toolResult?: unknown
  turnData?: Turn
  streaming?: boolean
}

export default function Playground() {
  const { activeAgent, setActiveAgent, fixtures, setFixtures } = useAppStore()
  const [agents, setAgents] = useState<Agent[]>([])
  const [session, setSession] = useState<Session | null>(null)
  const [selectedFixtureIds, setSelectedFixtureIds] = useState<string[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [selectedTurn, setSelectedTurn] = useState<Turn | null>(null)
  const [toolOverrides, setToolOverrides] = useState<Record<string, { data: unknown; active: boolean }>>({})
  const wsRef = useRef<ChatWebSocket | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [isStreaming, setIsStreaming] = useState(false)

  // Load agents and fixtures on mount
  useEffect(() => {
    api.listAgents().then(setAgents)
    api.listFixtures().then(setFixtures)
  }, [setFixtures])

  // Create session and connect WebSocket when agent is selected
  const startSession = useCallback(async (agent: Agent) => {
    // Disconnect existing
    if (wsRef.current) {
      wsRef.current.disconnect()
      wsRef.current = null
    }

    const sess = await api.createSession({
      agent_id: agent.id,
      fixture_ids: selectedFixtureIds,
    })
    setSession(sess)
    setMessages([])
    setSelectedTurn(null)

    const ws = new ChatWebSocket(sess.id)
    wsRef.current = ws

    ws.onMessage((msg: WsServerMessage) => {
      handleWsMessage(msg)
    })

    try {
      await ws.connect()
      setWsConnected(true)
    } catch {
      setMessages((prev) => [...prev, { role: 'system', content: 'Failed to connect to WebSocket' }])
    }
  }, [selectedFixtureIds])

  const handleWsMessage = (msg: WsServerMessage) => {
    switch (msg.type) {
      case 'agent_chunk':
        setMessages((prev) => {
          const last = prev[prev.length - 1]
          if (last?.streaming) {
            return [...prev.slice(0, -1), { ...last, content: last.content + msg.content }]
          }
          return [...prev, { role: 'agent', content: msg.content, streaming: true }]
        })
        break

      case 'tool_call':
        setMessages((prev) => [
          ...prev,
          {
            role: 'tool_call',
            content: `${msg.tool_name}(${JSON.stringify(msg.arguments)})`,
            toolCall: { name: msg.tool_name, args: msg.arguments },
          },
        ])
        break

      case 'tool_response':
        setMessages((prev) => [
          ...prev,
          {
            role: 'tool_response',
            content: JSON.stringify(msg.result, null, 2),
            toolResult: msg.result,
          },
        ])
        break

      case 'turn_complete':
        setMessages((prev) => {
          const updated = prev.map((m) =>
            m.streaming ? { ...m, streaming: false, id: msg.turn.id, turnData: msg.turn } : m
          )
          return updated
        })
        setIsStreaming(false)
        break

      case 'error':
        setMessages((prev) => [...prev, { role: 'system', content: `Error: ${msg.message}` }])
        setIsStreaming(false)
        break

      default:
        break
    }
  }

  const sendMessage = (content: string) => {
    if (!wsRef.current?.connected || isStreaming) return
    setIsStreaming(true)
    setMessages((prev) => [...prev, { role: 'user', content }])
    wsRef.current.send({ type: 'user_message', content })
  }

  const handleRerun = (turnId: string, overrides: Record<string, unknown>) => {
    if (!wsRef.current?.connected) return
    setIsStreaming(true)
    wsRef.current.send({ type: 'rerun_turn', turn_id: turnId, overrides })
  }

  const handleSwapFixture = () => {
    if (!wsRef.current?.connected) return
    wsRef.current.send({ type: 'swap_fixture', fixture_ids: selectedFixtureIds })
  }

  const handleSetToolOverride = (overrides: Record<string, { data: unknown; active: boolean }>) => {
    setToolOverrides(overrides)
    if (wsRef.current?.connected) {
      wsRef.current.send({ type: 'set_tool_override', overrides })
    }
  }

  const handleClearToolOverrides = () => {
    setToolOverrides({})
    if (wsRef.current?.connected) {
      wsRef.current.send({ type: 'clear_tool_overrides' })
    }
  }

  const handleAgentSelect = (agent: Agent) => {
    setActiveAgent(agent)
    startSession(agent)
  }

  const handleAgentUpdate = async (updates: Partial<Agent>) => {
    if (!activeAgent) return
    const updated = await api.updateAgent(activeAgent.id, updates)
    setActiveAgent(updated)
    setAgents((prev) => prev.map((a) => (a.id === updated.id ? updated : a)))
  }

  const handleSaveVersion = async (label: string) => {
    if (!activeAgent) return
    await api.createVersion(activeAgent.id, label)
  }

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.disconnect()
    }
  }, [])

  return (
    <div className="h-full grid grid-cols-[280px_1fr_340px] gap-0">
      <AgentConfigPanel
        agents={agents}
        activeAgent={activeAgent}
        fixtures={fixtures}
        selectedFixtureIds={selectedFixtureIds}
        onAgentSelect={handleAgentSelect}
        onAgentUpdate={handleAgentUpdate}
        onFixtureSelect={setSelectedFixtureIds}
        onSwapFixture={handleSwapFixture}
        onSaveVersion={handleSaveVersion}
        toolOverrides={toolOverrides}
        onSetToolOverride={handleSetToolOverride}
        onClearToolOverrides={handleClearToolOverrides}
        sessionActive={!!session}
      />
      <ChatPanel
        messages={messages}
        onSendMessage={sendMessage}
        onSelectTurn={setSelectedTurn}
        isStreaming={isStreaming}
        wsConnected={wsConnected}
        sessionActive={!!session}
      />
      <DebugPanel
        selectedTurn={selectedTurn}
        onRerun={handleRerun}
      />
    </div>
  )
}
