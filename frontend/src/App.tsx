import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Playground from './pages/Playground'
import Autorater from './pages/Autorater'
import Generator from './pages/Generator'
import Classification from './pages/Classification'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/playground" replace />} />
          <Route path="playground" element={<Playground />} />
          <Route path="autorater" element={<Autorater />} />
          <Route path="generator" element={<Generator />} />
          <Route path="classification" element={<Classification />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
