import { useState, useEffect } from 'react'
import { NavLink } from 'react-router-dom'
import {
  MessagesSquare,
  Bot,
  Users,
  ClipboardCheck,
  Tags,
  Settings,
  ChevronsRight,
  ChevronsLeft,
  type LucideIcon,
} from 'lucide-react'

interface NavItem {
  to: string
  icon: LucideIcon
  label: string
}

const topItems: NavItem[] = [
  { to: '/playground', icon: MessagesSquare, label: 'Playground' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/profiles', icon: Users, label: 'Profiles' },
  { to: '/autorater', icon: ClipboardCheck, label: 'Autorater' },
  { to: '/classification', icon: Tags, label: 'Classification' },
]

const bottomItems: NavItem[] = [
  { to: '/settings', icon: Settings, label: 'Settings' },
]

const STORAGE_KEY = 'iconRailCollapsed'

function RailLink({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        `group relative flex items-center h-10 rounded-lg transition-all duration-150 ${
          collapsed ? 'justify-center w-10' : 'justify-start w-full px-3 gap-2.5'
        } ${
          isActive
            ? 'bg-indigo-50 text-indigo-600'
            : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
        }`
      }
    >
      <Icon size={20} strokeWidth={1.75} className="shrink-0" />
      {collapsed ? (
        <span className="absolute left-full ml-2 px-2 py-1 text-xs font-medium text-white bg-slate-800 rounded-md opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity duration-150 z-50">
          {item.label}
        </span>
      ) : (
        <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden">
          {item.label}
        </span>
      )}
    </NavLink>
  )
}

export default function IconRail() {
  const [collapsed, setCollapsed] = useState(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored === null ? true : stored === 'true'
  })

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, String(collapsed))
  }, [collapsed])

  return (
    <div
      className={`flex flex-col h-full bg-white border-r border-slate-200 py-3 shrink-0 transition-all duration-200 overflow-hidden ${
        collapsed ? 'w-14 items-center' : 'w-[200px]'
      }`}
    >
      {/* Brand mark */}
      <div className={`flex items-center mb-4 ${collapsed ? 'justify-center' : 'px-3 gap-2'}`}>
        <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-600 text-white font-bold text-sm select-none shrink-0">
          PW
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold text-slate-700 whitespace-nowrap overflow-hidden">
            Workbench
          </span>
        )}
      </div>

      {/* Main nav */}
      <nav className={`flex flex-col gap-1 flex-1 ${collapsed ? 'items-center' : 'px-2'}`}>
        {topItems.map((item) => (
          <RailLink key={item.to} item={item} collapsed={collapsed} />
        ))}
      </nav>

      {/* Bottom nav */}
      <nav className={`flex flex-col gap-1 ${collapsed ? 'items-center' : 'px-2'}`}>
        {bottomItems.map((item) => (
          <RailLink key={item.to} item={item} collapsed={collapsed} />
        ))}
        {/* Toggle button */}
        <button
          onClick={() => setCollapsed((prev) => !prev)}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className={`flex items-center h-10 rounded-lg transition-all duration-150 text-slate-400 hover:text-slate-600 hover:bg-slate-100 ${
            collapsed ? 'justify-center w-10' : 'justify-start w-full px-3 gap-2.5'
          }`}
        >
          {collapsed ? (
            <ChevronsRight size={20} strokeWidth={1.75} />
          ) : (
            <ChevronsLeft size={20} strokeWidth={1.75} />
          )}
          {!collapsed && (
            <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden">
              Collapse
            </span>
          )}
        </button>
      </nav>
    </div>
  )
}
