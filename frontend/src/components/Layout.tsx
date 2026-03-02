import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import IconRail from './IconRail'
import TopBar from './TopBar'
import { useBackendLogs } from '../hooks/useBackendLogs'
import { onDevLog } from '../lib/devlog'
import { useDevLogStore } from '../store/devLogStore'

function DevLogBridge() {
  // Connect backend SSE stream
  useBackendLogs()

  // Forward frontend devlog events into the store
  const addEntry = useDevLogStore((s) => s.addEntry)
  useEffect(() => {
    return onDevLog(addEntry)
  }, [addEntry])

  return null
}

export default function Layout() {
  return (
    <div className="h-screen flex flex-row bg-slate-50">
      <DevLogBridge />
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
