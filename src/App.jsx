import React, { useState } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Topbar from './components/Topbar'
import Dashboard from './pages/Dashboard'
import Analytics from './pages/Analytics'
import MapView from './pages/MapView'
import './App.css'

function App() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  return (
    <Router>
      <div className="app-shell">
        <Sidebar isOpen={isSidebarOpen} setIsOpen={setIsSidebarOpen} />
        <div className="app-main">
          <Topbar onMenuClick={() => setIsSidebarOpen(true)} />
          <main className="app-body">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/map" element={<MapView />} />
              <Route path="*" element={<Navigate to="/dashboard" />} />
            </Routes>
          </main>
        </div>
      </div>
    </Router>
  )
}


export default App
