import { useLocation } from 'react-router-dom'

const pageTitles: Record<string, string> = {
  '/playground': 'Playground',
  '/agents': 'Agents',
  '/profiles': 'User Profiles',
  '/autorater': 'Autorater',
  '/generator': 'Transcript Generator',
  '/classification': 'Classification',
  '/settings': 'Settings',
}

interface TopBarProps {
  children?: React.ReactNode
}

export default function TopBar({ children }: TopBarProps) {
  const location = useLocation()
  const path = '/' + location.pathname.split('/')[1]
  const title = pageTitles[path] || 'Workbench'

  return (
    <div className="flex items-center justify-between h-12 px-5 bg-slate-50/80 border-b border-slate-200 shrink-0">
      <h1 className="text-[13px] font-semibold text-slate-800">{title}</h1>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  )
}
