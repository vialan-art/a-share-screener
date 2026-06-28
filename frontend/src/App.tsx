import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Routes, Route, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Screener from './pages/Screener'
import StockDetail from './pages/StockDetail'
import History from './pages/History'
import Logs from './pages/Logs'
import Advisor from './pages/Advisor'

function App() {
  const location = useLocation()

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="screener" element={<Screener />} />
        <Route path="stock/:symbol" element={<StockDetail />} />
        <Route path="history" element={<History />} />
        <Route path="logs" element={<Logs />} />
        <Route path="advisor" element={<Advisor />} />
      </Route>
    </Routes>
  )
}

export default App
