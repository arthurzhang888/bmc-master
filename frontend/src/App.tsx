import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ServerList from './pages/ServerList'
import ServerDetail from './pages/ServerDetail'
import Login from './pages/Login'
import EventCenter from './pages/EventCenter'
import Reports from './pages/Reports'
import Automation from './pages/Automation'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Dashboard />} />
        <Route path="/servers" element={<ServerList />} />
        <Route path="/servers/:id" element={<ServerDetail />} />
        <Route path="/events" element={<EventCenter />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/automation" element={<Automation />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
