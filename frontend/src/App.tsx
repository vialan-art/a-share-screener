import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Screener from './pages/Screener'
import StockDetail from './pages/StockDetail'
import History from './pages/History'
import Logs from './pages/Logs'
import Advisor from './pages/Advisor'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Overview />} />
        <Route path="screener" element={<Screener />} />
        <Route path="stock/:symbol" element={<StockDetail />} />
        <Route path="history" element={<History />} />
        <Route path="logs" element={<Logs />} />
        <Route path="advisor" element={<Advisor />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
