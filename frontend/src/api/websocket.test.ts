/**
 * Tests for the ChatWebSocket client.
 *
 * Focus: connection lifecycle, message dispatch, handler registration/removal,
 *        reconnect prevention on disconnect, and the connected getter.
 */

import { ChatWebSocket } from './websocket'

// Class-based WebSocket mock. Each constructed instance is tracked in
// MockWs.instances so tests can access it without sharing mutable state.
class MockWs {
  static OPEN = 1
  static CLOSED = 3
  static instances: MockWs[] = []

  url: string
  readyState = MockWs.OPEN
  onopen: (() => void) | null = null
  onmessage: ((e: { data: string }) => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((e: unknown) => void) | null = null
  send = vi.fn()
  close = vi.fn()

  constructor(url: string) {
    this.url = url
    MockWs.instances.push(this)
  }

  triggerOpen() { this.onopen?.() }
  triggerMessage(payload: unknown) { this.onmessage?.({ data: JSON.stringify(payload) }) }
  triggerClose() { this.onclose?.() }
  triggerError(err: unknown) { this.onerror?.(err) }
}

// Returns the most recently constructed MockWs instance.
function lastWs(): MockWs {
  return MockWs.instances[MockWs.instances.length - 1]
}

beforeEach(() => {
  MockWs.instances = []
  vi.stubGlobal('WebSocket', MockWs)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('connect()', () => {
  it('resolves when the WebSocket opens', async () => {
    const chat = new ChatWebSocket('session-1')
    const p = chat.connect()
    lastWs().triggerOpen()
    await expect(p).resolves.toBeUndefined()
  })

  it('rejects when the WebSocket errors before opening', async () => {
    const chat = new ChatWebSocket('session-1')
    const p = chat.connect()
    lastWs().triggerError(new Error('connection refused'))
    await expect(p).rejects.toBeTruthy()
  })

  it('constructs ws:// URL when page is http', async () => {
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:5173' },
      writable: true,
    })
    const chat = new ChatWebSocket('abc')
    const p = chat.connect()
    lastWs().triggerOpen()
    await p
    expect(lastWs().url).toBe('ws://localhost:5173/ws/chat/abc')
  })

  it('constructs wss:// URL when page is https', async () => {
    Object.defineProperty(window, 'location', {
      value: { protocol: 'https:', host: 'app.example.com' },
      writable: true,
    })
    const chat = new ChatWebSocket('xyz')
    const p = chat.connect()
    lastWs().triggerOpen()
    await p
    expect(lastWs().url).toBe('wss://app.example.com/ws/chat/xyz')
  })

  it('resets reconnectAttempts to 0 on successful open', async () => {
    const chat = new ChatWebSocket('s1')
    ;(chat as unknown as { reconnectAttempts: number }).reconnectAttempts = 3
    const p = chat.connect()
    lastWs().triggerOpen()
    await p
    expect((chat as unknown as { reconnectAttempts: number }).reconnectAttempts).toBe(0)
  })
})

describe('send()', () => {
  it('JSON-stringifies and sends the message when connected', async () => {
    const chat = new ChatWebSocket('s1')
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    chat.send({ type: 'user_message', content: 'Hello!' })
    expect(lastWs().send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'user_message', content: 'Hello!' }),
    )
  })

  it('does not send when connect() has not been called', () => {
    const chat = new ChatWebSocket('s1')
    // No ws instance created yet; send should be a no-op.
    chat.send({ type: 'user_message', content: 'Hello!' })
    // No MockWs instance was constructed, so nothing to assert on
    expect(MockWs.instances).toHaveLength(0)
  })
})

describe('onMessage()', () => {
  it('calls registered handler when a message arrives', async () => {
    const handler = vi.fn()
    const chat = new ChatWebSocket('s1')
    chat.onMessage(handler)
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    lastWs().triggerMessage({ type: 'agent_chunk', content: 'hi' })
    expect(handler).toHaveBeenCalledWith({ type: 'agent_chunk', content: 'hi' })
  })

  it('returns an unsubscribe function that removes the handler', async () => {
    const handler = vi.fn()
    const chat = new ChatWebSocket('s1')
    const unsubscribe = chat.onMessage(handler)
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    unsubscribe()
    lastWs().triggerMessage({ type: 'agent_chunk', content: 'hi' })
    expect(handler).not.toHaveBeenCalled()
  })

  it('calls all registered handlers for each message', async () => {
    const h1 = vi.fn()
    const h2 = vi.fn()
    const chat = new ChatWebSocket('s1')
    chat.onMessage(h1)
    chat.onMessage(h2)
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    lastWs().triggerMessage({ type: 'error', message: 'oops' })
    expect(h1).toHaveBeenCalledTimes(1)
    expect(h2).toHaveBeenCalledTimes(1)
  })

  it('silently ignores messages that are not valid JSON', async () => {
    const handler = vi.fn()
    const chat = new ChatWebSocket('s1')
    chat.onMessage(handler)
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    lastWs().onmessage?.({ data: 'not-valid-json{{' })
    expect(handler).not.toHaveBeenCalled()
  })
})

describe('disconnect()', () => {
  it('calls close() on the underlying WebSocket', async () => {
    const chat = new ChatWebSocket('s1')
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    chat.disconnect()
    expect(lastWs().close).toHaveBeenCalled()
  })

  it('clears all message handlers', async () => {
    const handler = vi.fn()
    const chat = new ChatWebSocket('s1')
    chat.onMessage(handler)
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    chat.disconnect()
    expect((chat as unknown as { handlers: unknown[] }).handlers).toHaveLength(0)
  })

  it('prevents automatic reconnect on subsequent close events', async () => {
    vi.useFakeTimers()
    const chat = new ChatWebSocket('s1')
    const p = chat.connect()
    lastWs().triggerOpen()
    await p

    const instancesBefore = MockWs.instances.length
    chat.disconnect()
    lastWs().triggerClose()
    vi.runAllTimers()

    // No additional WebSocket instances should have been created
    expect(MockWs.instances.length).toBe(instancesBefore)
  })
})

describe('connected getter', () => {
  it('returns false before connect() is called', () => {
    const chat = new ChatWebSocket('s1')
    expect(chat.connected).toBe(false)
  })

  it('returns true after a successful connection', async () => {
    const chat = new ChatWebSocket('s1')
    const p = chat.connect()
    lastWs().triggerOpen()
    await p
    expect(chat.connected).toBe(true)
  })
})
