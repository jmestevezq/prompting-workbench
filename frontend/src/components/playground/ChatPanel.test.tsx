import { render, screen, fireEvent } from '@testing-library/react'
import { vi, beforeAll } from 'vitest'
import ChatPanel from './ChatPanel'
import type { Turn } from '../../api/types'

// jsdom does not implement scrollIntoView — mock it globally
beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn()
})

const noopTurn: Turn = {
  id: 'turn-1',
  session_id: 'session-1',
  turn_index: 0,
  role: 'agent',
  content: '',
  is_active: 1,
  created_at: '',
}

function makeProps(overrides: Partial<Parameters<typeof ChatPanel>[0]> = {}) {
  return {
    messages: [],
    onSendMessage: vi.fn(),
    onSelectTurn: vi.fn(),
    isStreaming: false,
    wsConnected: false,
    sessionActive: false,
    ...overrides,
  }
}

describe('ChatPanel — basic rendering', () => {
  it('shows "Select an agent to start chatting" when no session is active', () => {
    render(<ChatPanel {...makeProps()} />)
    expect(screen.getByText(/select an agent/i)).toBeInTheDocument()
  })

  it('shows "Connected" when wsConnected and sessionActive', () => {
    render(<ChatPanel {...makeProps({ wsConnected: true, sessionActive: true })} />)
    expect(screen.getByText('Connected')).toBeInTheDocument()
  })

  it('shows "Generating..." indicator while streaming', () => {
    render(<ChatPanel {...makeProps({ isStreaming: true, sessionActive: true })} />)
    expect(screen.getByText('Generating...')).toBeInTheDocument()
  })

  it('disables send button when no session', () => {
    render(<ChatPanel {...makeProps()} />)
    const btn = screen.getByRole('button', { name: /send/i })
    expect(btn).toBeDisabled()
  })

  it('sends message on form submit', () => {
    const onSend = vi.fn()
    render(<ChatPanel {...makeProps({ sessionActive: true, wsConnected: true, onSendMessage: onSend })} />)
    const input = screen.getByRole('textbox')
    fireEvent.change(input, { target: { value: 'Hello agent' } })
    fireEvent.submit(input.closest('form')!)
    expect(onSend).toHaveBeenCalledWith('Hello agent')
  })
})

describe('ChatPanel — widget rendering', () => {
  const pieChartJson = JSON.stringify({
    pieChartBlock: {
      slices: [
        { label: 'Food', value: 500 },
        { label: 'Transport', value: 200 },
        { label: 'Entertainment', value: 300 },
      ],
    },
  })

  const lineChartJson = JSON.stringify({
    lineChartBlock: {
      dataPoints: [
        { x: 'Jan', y: 1200 },
        { x: 'Feb', y: 1500 },
        { x: 'Mar', y: 1100 },
      ],
    },
  })

  const tableJson = JSON.stringify({
    tableBlock: {
      title: 'Spending Summary',
      headers: [{ text: 'Category' }, { text: 'Amount' }],
      rows: [
        { cells: [{ textCell: { text: 'Food' } }, { textCell: { text: '₹500' } }] },
        { cells: [{ textCell: { text: 'Transport' } }, { textCell: { text: '₹200' } }] },
      ],
    },
  })

  const suggestionsJson = JSON.stringify({
    promptSuggestionsBlock: {
      suggestions: [
        'Show my top 5 spending categories',
        'What did I spend on food this month?',
      ],
    },
  })

  it('renders a pie chart from agent message JSON', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [
        { role: 'agent', content: pieChartJson },
      ],
    })
    render(<ChatPanel {...props} />)
    // Legend labels appear in the component
    expect(screen.getByText('Food')).toBeInTheDocument()
    expect(screen.getByText('Transport')).toBeInTheDocument()
    expect(screen.getByText('Entertainment')).toBeInTheDocument()
    // SVG pie chart is rendered
    expect(document.querySelector('svg')).toBeInTheDocument()
  })

  it('renders a line chart from agent message JSON', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [{ role: 'agent', content: lineChartJson }],
    })
    render(<ChatPanel {...props} />)
    // X-axis labels appear as SVG text elements
    expect(screen.getByText('Jan')).toBeInTheDocument()
    expect(screen.getByText('Feb')).toBeInTheDocument()
    expect(screen.getByText('Mar')).toBeInTheDocument()
    // SVG line chart is rendered
    expect(document.querySelector('svg')).toBeInTheDocument()
  })

  it('renders a table widget from agent message JSON', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [{ role: 'agent', content: tableJson }],
    })
    render(<ChatPanel {...props} />)
    expect(screen.getByText('Spending Summary')).toBeInTheDocument()
    expect(screen.getByText('Category')).toBeInTheDocument()
    expect(screen.getByText('Amount')).toBeInTheDocument()
    expect(screen.getByText('₹500')).toBeInTheDocument()
    expect(screen.getByText('₹200')).toBeInTheDocument()
  })

  it('renders prompt suggestion chips from agent message JSON', () => {
    const onSend = vi.fn()
    const props = makeProps({
      sessionActive: true,
      onSendMessage: onSend,
      messages: [{ role: 'agent', content: suggestionsJson }],
    })
    render(<ChatPanel {...props} />)
    expect(screen.getByText('Show my top 5 spending categories')).toBeInTheDocument()
    expect(screen.getByText('What did I spend on food this month?')).toBeInTheDocument()
  })

  it('sends suggestion text when a chip is clicked', () => {
    const onSend = vi.fn()
    const props = makeProps({
      sessionActive: true,
      onSendMessage: onSend,
      messages: [{ role: 'agent', content: suggestionsJson }],
    })
    render(<ChatPanel {...props} />)
    fireEvent.click(screen.getByText('Show my top 5 spending categories'))
    expect(onSend).toHaveBeenCalledWith('Show my top 5 spending categories')
  })

  it('shows "raw message toggle" button for widget messages', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [{ role: 'agent', content: pieChartJson }],
    })
    render(<ChatPanel {...props} />)
    expect(screen.getByText('raw message toggle')).toBeInTheDocument()
  })

  it('toggles to JSON view when "raw message toggle" is clicked', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [{ role: 'agent', content: pieChartJson }],
    })
    render(<ChatPanel {...props} />)
    fireEvent.click(screen.getByText('raw message toggle'))
    // In JSON view, raw content is shown in a <pre> block
    expect(screen.getByText(pieChartJson)).toBeInTheDocument()
  })

  it('renders fenced json block within mixed content', () => {
    const mixedContent = 'Here is your spending breakdown:\n```json\n' + pieChartJson + '\n```'
    const props = makeProps({
      sessionActive: true,
      messages: [{ role: 'agent', content: mixedContent }],
    })
    render(<ChatPanel {...props} />)
    expect(screen.getByText('Food')).toBeInTheDocument()
  })

  it('does not treat streaming messages as widget content', () => {
    const props = makeProps({
      sessionActive: true,
      isStreaming: true,
      messages: [{ role: 'agent', content: pieChartJson, streaming: true }],
    })
    render(<ChatPanel {...props} />)
    // While streaming, widget parsing is skipped — chart SVG titles should not appear
    expect(screen.queryByTitle(/food: /i)).not.toBeInTheDocument()
  })
})

describe('ChatPanel — user and tool messages', () => {
  it('renders user messages right-aligned', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [{ role: 'user', content: 'Hello from user' }],
    })
    render(<ChatPanel {...props} />)
    expect(screen.getByText('Hello from user')).toBeInTheDocument()
  })

  it('renders tool_call messages', () => {
    const props = makeProps({
      sessionActive: true,
      messages: [{
        role: 'tool_call',
        content: '',
        toolCall: { name: 'GET_TRANSACTION_HISTORY', args: { limit: 10 } },
      }],
    })
    render(<ChatPanel {...props} />)
    // Tool call is shown inside a <details> summary as "Tool Call: <name>"
    expect(screen.getByText(/Tool Call: GET_TRANSACTION_HISTORY/)).toBeInTheDocument()
  })

  it('calls onSelectTurn when an agent message with turnData is clicked', () => {
    const onSelect = vi.fn()
    const turn = { ...noopTurn, content: 'Agent response' }
    const props = makeProps({
      sessionActive: true,
      onSelectTurn: onSelect,
      messages: [{ role: 'agent' as const, content: 'Agent response', turnData: turn }],
    })
    render(<ChatPanel {...props} />)
    fireEvent.click(screen.getByText('Agent response'))
    expect(onSelect).toHaveBeenCalledWith(turn)
  })
})
