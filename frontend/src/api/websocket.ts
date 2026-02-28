import type { WsClientMessage, WsServerMessage } from './types'

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
        resolve()
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as WsServerMessage
          this.handlers.forEach((handler) => handler(message))
        } catch {
          console.error('Failed to parse WebSocket message:', event.data)
        }
      }

      this.ws.onclose = () => {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++
          setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        reject(error)
      }
    })
  }

  send(message: WsClientMessage) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
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
