import { NavLink, Outlet } from 'react-router-dom'

const navItems = [
  { to: '/playground', label: 'Playground' },
  { to: '/autorater', label: 'Autorater' },
  { to: '/generator', label: 'Generator' },
  { to: '/classification', label: 'Classification' },
  { to: '/settings', label: 'Settings' },
]

export default function Layout() {
  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <nav className="bg-white border-b border-gray-200 px-4 py-2 flex items-center gap-1 shrink-0">
        <span className="font-semibold text-gray-800 mr-6 text-sm">Prompt Workbench</span>
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `px-3 py-1.5 rounded text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-blue-100 text-blue-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}
