import type { LucideIcon } from 'lucide-react'

export interface SubNavItem {
  key: string
  label: string
  icon?: LucideIcon
  count?: number
}

interface SubNavProps {
  items: SubNavItem[]
  active: string
  onChange: (key: string) => void
}

export default function SubNav({ items, active, onChange }: SubNavProps) {
  return (
    <nav className="flex flex-col w-[180px] bg-white border-r border-slate-200 py-3 shrink-0">
      {items.map((item) => {
        const isActive = active === item.key
        const Icon = item.icon
        return (
          <button
            key={item.key}
            onClick={() => onChange(item.key)}
            className={`flex items-center gap-2 px-4 py-2 text-[13px] font-medium text-left transition-all duration-150 border-l-2 ${
              isActive
                ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                : 'border-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-800'
            }`}
          >
            {Icon && <Icon size={16} strokeWidth={1.75} />}
            <span className="flex-1">{item.label}</span>
            {item.count !== undefined && (
              <span className={`text-xs tabular-nums ${isActive ? 'text-indigo-500' : 'text-slate-400'}`}>
                {item.count}
              </span>
            )}
          </button>
        )
      })}
    </nav>
  )
}
