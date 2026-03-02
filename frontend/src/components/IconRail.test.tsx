import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import IconRail from './IconRail'

beforeEach(() => {
  localStorage.clear()
})

function renderIconRail(initialRoute = '/playground') {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <IconRail />
    </MemoryRouter>,
  )
}

describe('IconRail', () => {
  it('renders the brand mark', () => {
    renderIconRail()
    expect(screen.getByText('PW')).toBeInTheDocument()
  })

  it('renders all navigation links with tooltips when collapsed', () => {
    renderIconRail()
    expect(screen.getByTitle('Playground')).toBeInTheDocument()
    expect(screen.getByTitle('Agents')).toBeInTheDocument()
    expect(screen.getByTitle('Profiles')).toBeInTheDocument()
    expect(screen.getByTitle('Autorater')).toBeInTheDocument()
    expect(screen.getByTitle('Classification')).toBeInTheDocument()
    expect(screen.getByTitle('Settings')).toBeInTheDocument()
  })

  it('applies active styling to the current route', () => {
    renderIconRail('/agents')
    const agentsLink = screen.getByTitle('Agents')
    expect(agentsLink.className).toContain('bg-indigo-50')
    expect(agentsLink.className).toContain('text-indigo-600')
  })

  it('applies inactive styling to non-active routes', () => {
    renderIconRail('/playground')
    const agentsLink = screen.getByTitle('Agents')
    expect(agentsLink.className).toContain('text-slate-400')
  })

  it('renders toggle button', () => {
    renderIconRail()
    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument()
  })

  it('starts collapsed by default (w-14)', () => {
    renderIconRail()
    const rail = screen.getByText('PW').closest('div[class*="border-r"]')!
    expect(rail.className).toContain('w-14')
  })

  it('expands when toggle is clicked', () => {
    renderIconRail()
    fireEvent.click(screen.getByLabelText('Expand sidebar'))
    const rail = screen.getByText('PW').closest('div[class*="border-r"]')!
    expect(rail.className).toContain('w-[200px]')
  })

  it('shows text labels when expanded', () => {
    renderIconRail()
    fireEvent.click(screen.getByLabelText('Expand sidebar'))
    // In expanded mode, labels are inline text, not just tooltips
    expect(screen.getByText('Workbench')).toBeInTheDocument()
    expect(screen.getByText('Collapse')).toBeInTheDocument()
  })

  it('persists collapsed state to localStorage', () => {
    renderIconRail()
    // Default collapsed
    expect(localStorage.getItem('iconRailCollapsed')).toBe('true')
    // Expand
    fireEvent.click(screen.getByLabelText('Expand sidebar'))
    expect(localStorage.getItem('iconRailCollapsed')).toBe('false')
  })

  it('reads initial state from localStorage', () => {
    localStorage.setItem('iconRailCollapsed', 'false')
    renderIconRail()
    const rail = screen.getByText('PW').closest('div[class*="border-r"]')!
    expect(rail.className).toContain('w-[200px]')
  })
})
