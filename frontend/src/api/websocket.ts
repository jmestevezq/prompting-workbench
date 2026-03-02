import type { WsClientMessage, WsServerMessage } from './types'
import { devLog } from '../lib/devlog'

export type MessageHandler = (message: WsServerMessage) => void

export class ChatWebSocket {
  private ws: WebSocket | null = null
  private sessionId: string
  private handlers: MessageHandler[] = []
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000

  constructor(sessionId: string) {
    this.sessionId = sessionId
  }

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const url = `${protocol}//${window.location.host}/ws/chat/${this.sessionId}`

      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        this.reconnectAttempts = 0
        devLog('WS_OUT', 'info', `WS connected — session=${this.sessionId.slice(0, 8)}`)
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WsServerMessage
          devLog('WS_IN', 'info', `WS ← ${message.type}`, message.type === 'agent_chunk' ? undefined : message)
          this.handlers.forEach((handler) => handler(message))
        } catch {
          console.error('Failed to parse WebSocket message:', event.data)
        }
      }

      this.ws.onclose = () => {
        devLog('WS_OUT', 'info', `WS closed — session=${this.sessionId.slice(0, 8)}`)
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts)
        }
      }

      this.ws.onerror = (error) => {
        devLog('WS_ERR', 'error', `WS error — session=${this.sessionId.slice(0, 8)}`, { error: String(error) })
        console.error('WebSocket error:', error)
        reject(error)
      }
    })
  }

  send(message: WsClientMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      devLog('WS_OUT', 'info', `WS → ${message.type}`, message.type === 'user_message' ? { content: (message as { type: string; content?: string }).content?.slice(0, 80) } : message)
      this.ws.send(JSON.stringify(message))
    } else {
      devLog('WS_ERR', 'warn', `WS send failed (not connected) — type=${message.type}`)
      console.error('WebSocket not connected')
    }
  }

  onMessage(handler: MessageHandler) {
    this.handlers.push(handler)
    return () => {
      this.handlers = this.handlers.filter((h) => h !== handler)
    }
  }

  disconnect() {
    this.maxReconnectAttempts = 0 // Prevent reconnect
    this.ws?.close()
    this.ws = null
    this.handlers = []
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
