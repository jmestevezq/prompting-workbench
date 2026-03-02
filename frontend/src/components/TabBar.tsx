import type { LucideIcon } from 'lucide-react'

export interface TabBarItem {
  key: string
  label: string
  icon?: LucideIcon
  count?: number
}

interface TabBarProps {
  items: TabBarItem[]
  active: string
  onChange: (key: string) => void
}

export default function TabBar({ items, active, onChange }: TabBarProps) {
  return (
    <div className="border-b border-slate-200 bg-white px-4">
      <nav className="flex gap-0">
        {items.map((item) => {
          const isActive = active === item.key
          const Icon = item.icon
          return (
            <button
              key={item.key}
              onClick={() => onChange(item.key)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-[13px] font-medium border-b-2 -mb-px transition-colors ${
                isActive
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
              }`}
            >
              {Icon && <Icon size={16} strokeWidth={1.75} />}
              <span>{item.label}</span>
              {item.count !== undefined && (
                <span className={`text-xs tabular-nums ${isActive ? 'text-indigo-400' : 'text-slate-400'}`}>
                  {item.count}
                </span>
              )}
            </button>
          )
        })}
      </nav>
    </div>
  )
}
