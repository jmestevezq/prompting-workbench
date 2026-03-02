import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import IconRail from './IconRail'

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

  it('renders all navigation links with tooltips', () => {
    renderIconRail()
    expect(screen.getByTitle('Playground')).toBeInTheDocument()
    expect(screen.getByTitle('Agents')).toBeInTheDocument()
    expect(screen.getByTitle('Profiles')).toBeInTheDocument()
    expect(screen.getByTitle('Autorater')).toBeInTheDocument()
    expect(screen.getByTitle('Generator')).toBeInTheDocument()
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
})
