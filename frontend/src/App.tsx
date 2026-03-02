import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Playground from './pages/Playground'
import Agents from './pages/Agents'
import UserProfiles from './pages/UserProfiles'
import Autorater from './pages/Autorater'
import Classification from './pages/Classification'
import DevLogs from './pages/DevLogs'
import Settings from './pages/Settings'
import { ToastProvider } from './components/ToastProvider'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/playground" replace />} />
            <Route path="playground" element={<Playground />} />
            <Route path="agents" element={<Agents />} />
            <Route path="profiles" element={<UserProfiles />} />
            <Route path="autorater" element={<Autorater />} />
            <Route path="classification" element={<Classification />} />
            <Route path="devlogs" element={<DevLogs />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
