import { Outlet } from 'react-router-dom'
import IconRail from './IconRail'
import TopBar from './TopBar'

export default function Layout() {
  return (
    <div className="h-screen flex flex-row bg-slate-50">
      <IconRail />
      <div className="flex flex-col flex-1 min-w-0">
        <TopBar />
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
