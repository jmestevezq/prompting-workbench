/**
 * Tests for the MetricsCard component.
 *
 * Focus: title rendering, key formatting, number display rules
 *        (percentage for 0<x<1, fixed-2 otherwise), and string pass-through.
 */

import { render, screen } from '@testing-library/react'
import MetricsCard from './MetricsCard'

describe('MetricsCard — title', () => {
  it('renders the provided title', () => {
    render(<MetricsCard title="Run Metrics" metrics={{}} />)
    expect(screen.getByText('Run Metrics')).toBeInTheDocument()
  })
})

describe('MetricsCard — key formatting', () => {
  it('replaces underscores with spaces in metric keys', () => {
    render(<MetricsCard title="M" metrics={{ pass_rate: 0.5 }} />)
    expect(screen.getByText('pass rate')).toBeInTheDocument()
  })

  it('displays multi-word keys with all underscores replaced', () => {
    render(<MetricsCard title="M" metrics={{ exact_match_rate: 0.9 }} />)
    expect(screen.getByText('exact match rate')).toBeInTheDocument()
  })

  it('renders plain keys without modification', () => {
    render(<MetricsCard title="M" metrics={{ f1: 0.8 }} />)
    expect(screen.getByText('f1')).toBeInTheDocument()
  })
})

describe('MetricsCard — number formatting', () => {
  it('formats fractions between 0 and 1 as percentages', () => {
    render(<MetricsCard title="M" metrics={{ precision: 0.75 }} />)
    expect(screen.getByText('75.0%')).toBeInTheDocument()
  })

  it('formats 0.5 as 50.0%', () => {
    render(<MetricsCard title="M" metrics={{ rate: 0.5 }} />)
    expect(screen.getByText('50.0%')).toBeInTheDocument()
  })

  it('formats integers >= 1 with two decimal places', () => {
    render(<MetricsCard title="M" metrics={{ total: 42 }} />)
    expect(screen.getByText('42.00')).toBeInTheDocument()
  })

  it('formats floats >= 1 with two decimal places', () => {
    render(<MetricsCard title="M" metrics={{ score: 1.5 }} />)
    expect(screen.getByText('1.50')).toBeInTheDocument()
  })

  it('formats exactly 0 with two decimal places (not as %)', () => {
    render(<MetricsCard title="M" metrics={{ zero: 0 }} />)
    expect(screen.getByText('0.00')).toBeInTheDocument()
  })

  it('formats exactly 1 with two decimal places (not as %)', () => {
    render(<MetricsCard title="M" metrics={{ one: 1 }} />)
    expect(screen.getByText('1.00')).toBeInTheDocument()
  })
})

describe('MetricsCard — string values', () => {
  it('displays string values directly without modification', () => {
    render(<MetricsCard title="M" metrics={{ status: 'pass' }} />)
    expect(screen.getByText('pass')).toBeInTheDocument()
  })

  it('displays mixed metrics correctly', () => {
    render(
      <MetricsCard
        title="Summary"
        metrics={{ pass_rate: 0.8, total: 10, label: 'v2' }}
      />,
    )
    expect(screen.getByText('80.0%')).toBeInTheDocument()
    expect(screen.getByText('10.00')).toBeInTheDocument()
    expect(screen.getByText('v2')).toBeInTheDocument()
  })
})

describe('MetricsCard — edge cases', () => {
  it('renders with empty metrics object without crashing', () => {
    const { container } = render(<MetricsCard title="Empty" metrics={{}} />)
    expect(container).toBeTruthy()
  })

  it('renders many metrics without crashing', () => {
    const metrics: Record<string, number> = {}
    for (let i = 0; i < 20; i++) metrics[`metric_${i}`] = i * 0.05
    const { container } = render(<MetricsCard title="Many" metrics={metrics} />)
    expect(container).toBeTruthy()
  })
})
