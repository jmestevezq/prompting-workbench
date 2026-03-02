import { NavLink } from 'react-router-dom'
import {
  MessagesSquare,
  Bot,
  Users,
  ClipboardCheck,
  Sparkles,
  Tags,
  Settings,
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
  { to: '/generator', icon: Sparkles, label: 'Generator' },
  { to: '/classification', icon: Tags, label: 'Classification' },
]

const bottomItems: NavItem[] = [
  { to: '/settings', icon: Settings, label: 'Settings' },
]

function RailLink({ item }: { item: NavItem }) {
  const Icon = item.icon
  return (
    <NavLink
      to={item.to}
      title={item.label}
      className={({ isActive }) =>
        `group relative flex items-center justify-center w-10 h-10 rounded-lg transition-all duration-150 ${
          isActive
            ? 'bg-indigo-50 text-indigo-600'
            : 'text-slate-400 hover:text-slate-600 hover:bg-slate-100'
        }`
      }
    >
      <Icon size={20} strokeWidth={1.75} />
      <span className="absolute left-full ml-2 px-2 py-1 text-xs font-medium text-white bg-slate-800 rounded-md opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap transition-opacity duration-150 z-50">
        {item.label}
      </span>
    </NavLink>
  )
}

export default function IconRail() {
  return (
    <div className="flex flex-col items-center w-14 h-full bg-white border-r border-slate-200 py-3 shrink-0">
      {/* Brand mark */}
      <div className="flex items-center justify-center w-9 h-9 rounded-lg bg-indigo-600 text-white font-bold text-sm mb-4 select-none">
        PW
      </div>

      {/* Main nav */}
      <nav className="flex flex-col items-center gap-1 flex-1">
        {topItems.map((item) => (
          <RailLink key={item.to} item={item} />
        ))}
      </nav>

      {/* Bottom nav */}
      <nav className="flex flex-col items-center gap-1">
        {bottomItems.map((item) => (
          <RailLink key={item.to} item={item} />
        ))}
      </nav>
    </div>
  )
}
