/**
 * Tests for the TranscriptPicker component.
 *
 * Focus: collapsed summary display, expand/collapse toggle, tag chip
 *        rendering with counts, tag-based bulk selection/deselection,
 *        and the underlying transcript table.
 */

import { render, screen, fireEvent } from '@testing-library/react'
import TranscriptPicker from './TranscriptPicker'
import type { Transcript } from '../api/types'

function makeTranscript(
  id: string,
  name: string,
  tags: string[] = [],
  source = 'manual',
): Transcript {
  return { id, name, content: '[USER] Hi', labels: {}, source, tags, created_at: '2024-01-01' }
}

const transcripts = [
  makeTranscript('1', 'Alpha', ['safety', 'math']),
  makeTranscript('2', 'Beta', ['safety']),
  makeTranscript('3', 'Gamma', []),
]

function renderPicker(
  selectedIds: Set<string> = new Set(),
  onChange = vi.fn(),
  items = transcripts,
) {
  return render(
    <TranscriptPicker
      transcripts={items}
      selectedIds={selectedIds}
      onSelectionChange={onChange}
    />,
  )
}

// The expand button shows "{n} of {total} transcripts ▼/▲"
function getExpandButton() {
  return screen.getByRole('button', { name: /transcripts/ })
}

describe('TranscriptPicker — collapsed state', () => {
  it('shows the selection count and total in the toggle button', () => {
    renderPicker(new Set(['1']))
    expect(screen.getByText(/1 of 3 transcripts/)).toBeInTheDocument()
  })

  it('shows ▼ indicator when collapsed', () => {
    renderPicker()
    expect(getExpandButton().textContent).toContain('▼')
  })

  it('does not render tag chips when collapsed', () => {
    renderPicker()
    expect(screen.queryByText(/safety/)).not.toBeInTheDocument()
  })

  it('does not render the transcript table when collapsed', () => {
    renderPicker()
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument()
  })
})

describe('TranscriptPicker — expand / collapse toggle', () => {
  it('expands when the toggle button is clicked', () => {
    renderPicker()
    fireEvent.click(getExpandButton())
    expect(screen.getByText('Alpha')).toBeInTheDocument()
  })

  it('shows ▲ indicator when expanded', () => {
    renderPicker()
    fireEvent.click(getExpandButton())
    expect(getExpandButton().textContent).toContain('▲')
  })

  it('collapses again when the toggle button is clicked a second time', () => {
    renderPicker()
    fireEvent.click(getExpandButton())
    fireEvent.click(getExpandButton())
    expect(screen.queryByText('Alpha')).not.toBeInTheDocument()
  })
})

describe('TranscriptPicker — tag chips', () => {
  it('renders a chip for each unique tag when expanded', () => {
    renderPicker()
    fireEvent.click(getExpandButton())
    // Chips show "tag (count)" — verify by the chip-specific text
    expect(screen.getByText('safety (2)')).toBeInTheDocument()
    expect(screen.getByText('math (1)')).toBeInTheDocument()
  })

  it('shows the count of transcripts with each tag', () => {
    renderPicker()
    fireEvent.click(getExpandButton())
    // 'safety' appears in 2 transcripts, 'math' in 1
    expect(screen.getByText('safety (2)')).toBeInTheDocument()
    expect(screen.getByText('math (1)')).toBeInTheDocument()
  })

  it('does not render chips when no transcript has tags', () => {
    const noTagItems = [makeTranscript('1', 'A'), makeTranscript('2', 'B')]
    renderPicker(new Set(), vi.fn(), noTagItems)
    fireEvent.click(getExpandButton())
    // No tag chip buttons beyond the expand toggle itself
    const allButtons = screen.getAllByRole('button')
    // Only the expand button should be present — no tag chips
    expect(allButtons).toHaveLength(1)
  })
})

describe('TranscriptPicker — tag-based bulk selection', () => {
  it('selects all transcripts with a tag when chip is clicked', () => {
    const onChange = vi.fn()
    renderPicker(new Set(), onChange)
    fireEvent.click(getExpandButton())
    fireEvent.click(screen.getByText('safety (2)'))

    const selected: Set<string> = onChange.mock.calls[0][0]
    expect(selected.has('1')).toBe(true)  // Alpha has safety
    expect(selected.has('2')).toBe(true)  // Beta has safety
    expect(selected.has('3')).toBe(false) // Gamma does not
  })

  it('deselects all transcripts with a tag when all are already selected', () => {
    const onChange = vi.fn()
    renderPicker(new Set(['1', '2']), onChange)
    fireEvent.click(getExpandButton())
    fireEvent.click(screen.getByText('safety (2)'))

    const selected: Set<string> = onChange.mock.calls[0][0]
    expect(selected.has('1')).toBe(false)
    expect(selected.has('2')).toBe(false)
  })

  it('preserves already-selected non-tag transcripts when selecting a tag', () => {
    const onChange = vi.fn()
    // '3' is already selected (no tags), now click 'math' chip
    renderPicker(new Set(['3']), onChange)
    fireEvent.click(getExpandButton())
    fireEvent.click(screen.getByText('math (1)'))

    const selected: Set<string> = onChange.mock.calls[0][0]
    expect(selected.has('1')).toBe(true)  // math transcript
    expect(selected.has('3')).toBe(true)  // previously selected
  })
})

describe('TranscriptPicker — transcript table', () => {
  it('shows all transcripts in the table when expanded', () => {
    renderPicker()
    fireEvent.click(getExpandButton())
    expect(screen.getByText('Alpha')).toBeInTheDocument()
    expect(screen.getByText('Beta')).toBeInTheDocument()
    expect(screen.getByText('Gamma')).toBeInTheDocument()
  })
})

describe('TranscriptPicker — edge cases', () => {
  it('handles an empty transcript list without crashing', () => {
    renderPicker(new Set(), vi.fn(), [])
    expect(screen.getByText(/0 of 0 transcripts/)).toBeInTheDocument()
  })

  it('shows correct count when all transcripts are selected', () => {
    renderPicker(new Set(['1', '2', '3']))
    expect(screen.getByText(/3 of 3 transcripts/)).toBeInTheDocument()
  })
})
