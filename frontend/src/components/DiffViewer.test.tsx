/**
 * Tests for the DiffViewer component.
 *
 * Focus: title rendering, content display, line-level change highlighting
 *        (red on left for removed, green on right for added), and
 *        graceful handling of unequal line counts and empty inputs.
 */

import { render, screen } from '@testing-library/react'
import DiffViewer from './DiffViewer'

describe('DiffViewer — titles', () => {
  it('uses "Before" as the default left title', () => {
    render(<DiffViewer left="a" right="a" />)
    expect(screen.getByText('Before')).toBeInTheDocument()
  })

  it('uses "After" as the default right title', () => {
    render(<DiffViewer left="a" right="a" />)
    expect(screen.getByText('After')).toBeInTheDocument()
  })

  it('renders custom left and right titles', () => {
    render(<DiffViewer left="x" right="y" leftTitle="v1.0" rightTitle="v2.0" />)
    expect(screen.getByText('v1.0')).toBeInTheDocument()
    expect(screen.getByText('v2.0')).toBeInTheDocument()
  })
})

describe('DiffViewer — content rendering', () => {
  it('renders the content of identical files without highlights', () => {
    const { container } = render(<DiffViewer left="same line" right="same line" />)
    expect(screen.getAllByText('same line').length).toBeGreaterThanOrEqual(1)
    expect(container.querySelectorAll('.bg-red-50')).toHaveLength(0)
    expect(container.querySelectorAll('.bg-green-50')).toHaveLength(0)
  })

  it('highlights the left side in red when lines differ', () => {
    const { container } = render(<DiffViewer left="old line" right="new line" />)
    const redLines = container.querySelectorAll('.bg-red-50')
    expect(redLines.length).toBeGreaterThan(0)
  })

  it('highlights the right side in green when lines differ', () => {
    const { container } = render(<DiffViewer left="old line" right="new line" />)
    const greenLines = container.querySelectorAll('.bg-green-50')
    expect(greenLines.length).toBeGreaterThan(0)
  })

  it('highlights only changed lines when some lines are the same', () => {
    const { container } = render(
      <DiffViewer left="same\nold text\nsame" right="same\nnew text\nsame" />,
    )
    // Only 1 line changed per side
    expect(container.querySelectorAll('.bg-red-50')).toHaveLength(1)
    expect(container.querySelectorAll('.bg-green-50')).toHaveLength(1)
  })

  it('does not highlight unchanged lines', () => {
    const { container } = render(
      <DiffViewer left="line1\nline2" right="line1\nline2" />,
    )
    expect(container.querySelectorAll('.bg-red-50')).toHaveLength(0)
    expect(container.querySelectorAll('.bg-green-50')).toHaveLength(0)
  })
})

describe('DiffViewer — unequal line counts', () => {
  it('handles left being longer than right without crashing', () => {
    const { container } = render(
      <DiffViewer left="line1\nline2\nline3" right="line1" />,
    )
    expect(container).toBeTruthy()
  })

  it('handles right being longer than left without crashing', () => {
    const { container } = render(
      <DiffViewer left="line1" right="line1\nline2\nline3" />,
    )
    expect(container).toBeTruthy()
  })

  it('marks extra left lines (no right counterpart) as changed', () => {
    const { container } = render(<DiffViewer left="a\nb" right="a" />)
    // "b" on the left has no counterpart on the right — should be highlighted
    expect(container.querySelectorAll('.bg-red-50').length).toBeGreaterThan(0)
  })

  it('marks extra right lines (no left counterpart) as changed', () => {
    const { container } = render(<DiffViewer left="a" right="a\nb" />)
    expect(container.querySelectorAll('.bg-green-50').length).toBeGreaterThan(0)
  })
})

describe('DiffViewer — edge cases', () => {
  it('renders without crashing when both inputs are empty strings', () => {
    const { container } = render(<DiffViewer left="" right="" />)
    expect(container).toBeTruthy()
  })

  it('renders without crashing for very long content', () => {
    const long = Array.from({ length: 100 }, (_, i) => `Line ${i}`).join('\n')
    const { container } = render(<DiffViewer left={long} right={long} />)
    expect(container).toBeTruthy()
  })
})
