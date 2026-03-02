import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import TopBar from './TopBar'

function renderTopBar(route = '/playground', children?: React.ReactNode) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <TopBar>{children}</TopBar>
    </MemoryRouter>,
  )
}

describe('TopBar', () => {
  it('renders the page title based on current route', () => {
    renderTopBar('/playground')
    expect(screen.getByText('Playground')).toBeInTheDocument()
  })

  it('renders correct title for agents route', () => {
    renderTopBar('/agents')
    expect(screen.getByText('Agents')).toBeInTheDocument()
  })

  it('renders correct title for settings route', () => {
    renderTopBar('/settings')
    expect(screen.getByText('Settings')).toBeInTheDocument()
  })

  it('renders children in the action slot', () => {
    renderTopBar('/playground', <button>Action</button>)
    expect(screen.getByText('Action')).toBeInTheDocument()
  })

  it('does not render action slot when no children', () => {
    const { container } = renderTopBar('/playground')
    // Only 1 child in the topbar (the title h1)
    const topbar = container.firstChild as HTMLElement
    expect(topbar.children).toHaveLength(1)
  })
})
