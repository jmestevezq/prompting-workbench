import { render, screen } from '@testing-library/react'
import StatusBadge from './StatusBadge'

describe('StatusBadge', () => {
  it('renders the status text', () => {
    render(<StatusBadge status="pass" />)
    expect(screen.getByText('pass')).toBeInTheDocument()
  })

  it('applies emerald styles for pass status', () => {
    render(<StatusBadge status="pass" />)
    const badge = screen.getByText('pass')
    expect(badge.className).toContain('bg-emerald-50')
    expect(badge.className).toContain('text-emerald-700')
  })

  it('applies rose styles for fail status', () => {
    render(<StatusBadge status="fail" />)
    const badge = screen.getByText('fail')
    expect(badge.className).toContain('bg-rose-50')
    expect(badge.className).toContain('text-rose-700')
  })

  it('applies slate fallback for unknown status', () => {
    render(<StatusBadge status="unknown" />)
    const badge = screen.getByText('unknown')
    expect(badge.className).toContain('bg-slate-100')
    expect(badge.className).toContain('text-slate-600')
  })

  it('accepts custom className', () => {
    render(<StatusBadge status="pass" className="ml-2" />)
    const badge = screen.getByText('pass')
    expect(badge.className).toContain('ml-2')
  })

  it('renders with rounded-full pill shape', () => {
    render(<StatusBadge status="pending" />)
    const badge = screen.getByText('pending')
    expect(badge.className).toContain('rounded-full')
  })
})
