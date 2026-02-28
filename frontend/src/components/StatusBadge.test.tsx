import { render, screen } from '@testing-library/react'
import StatusBadge from './StatusBadge'

describe('StatusBadge', () => {
  it('renders the status text', () => {
    render(<StatusBadge status="pass" />)
    expect(screen.getByText('pass')).toBeInTheDocument()
  })

  it('applies green styles for pass status', () => {
    render(<StatusBadge status="pass" />)
    const badge = screen.getByText('pass')
    expect(badge.className).toContain('bg-green-100')
    expect(badge.className).toContain('text-green-700')
  })

  it('applies red styles for fail status', () => {
    render(<StatusBadge status="fail" />)
    const badge = screen.getByText('fail')
    expect(badge.className).toContain('bg-red-100')
    expect(badge.className).toContain('text-red-700')
  })

  it('applies gray fallback for unknown status', () => {
    render(<StatusBadge status="unknown" />)
    const badge = screen.getByText('unknown')
    expect(badge.className).toContain('bg-gray-100')
    expect(badge.className).toContain('text-gray-700')
  })

  it('accepts custom className', () => {
    render(<StatusBadge status="pass" className="ml-2" />)
    const badge = screen.getByText('pass')
    expect(badge.className).toContain('ml-2')
  })
})
