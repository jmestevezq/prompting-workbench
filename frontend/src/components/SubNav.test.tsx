import { render, screen, fireEvent } from '@testing-library/react'
import SubNav from './SubNav'

const items = [
  { key: 'tab1', label: 'First Tab' },
  { key: 'tab2', label: 'Second Tab' },
  { key: 'tab3', label: 'Third Tab', count: 5 },
]

describe('SubNav', () => {
  it('renders all items', () => {
    render(<SubNav items={items} active="tab1" onChange={() => {}} />)
    expect(screen.getByText('First Tab')).toBeInTheDocument()
    expect(screen.getByText('Second Tab')).toBeInTheDocument()
    expect(screen.getByText('Third Tab')).toBeInTheDocument()
  })

  it('shows count badge when provided', () => {
    render(<SubNav items={items} active="tab1" onChange={() => {}} />)
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('applies active styling to the active item', () => {
    render(<SubNav items={items} active="tab1" onChange={() => {}} />)
    const activeBtn = screen.getByText('First Tab').closest('button')!
    expect(activeBtn.className).toContain('border-indigo-500')
    expect(activeBtn.className).toContain('text-indigo-700')
  })

  it('applies inactive styling to non-active items', () => {
    render(<SubNav items={items} active="tab1" onChange={() => {}} />)
    const inactiveBtn = screen.getByText('Second Tab').closest('button')!
    expect(inactiveBtn.className).toContain('text-slate-600')
    expect(inactiveBtn.className).toContain('border-transparent')
  })

  it('calls onChange with the item key when clicked', () => {
    const onChange = vi.fn()
    render(<SubNav items={items} active="tab1" onChange={onChange} />)
    fireEvent.click(screen.getByText('Second Tab'))
    expect(onChange).toHaveBeenCalledWith('tab2')
  })
})
