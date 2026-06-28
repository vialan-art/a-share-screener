import { Outlet, NavLink } from 'react-router-dom'
import { BarChart3, List, History, MessageCircle, Activity } from 'lucide-react'

function NavItem({ to, icon: Icon, label }: { to: string; icon: React.ElementType; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
          isActive ? 'bg-blue-600 text-white' : 'text-gray-600 hover:bg-gray-100'
        }`
      }
    >
      <Icon size={18} />
      <span>{label}</span>
    </NavLink>
  )
}

export default function Layout() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-64 bg-white border-r border-gray-200 p-4">
        <div className="mb-8">
          <h1 className="text-xl font-bold text-blue-700">A-Share Screener</h1>
          <p className="text-xs text-gray-500 mt-1">A股选股研究系统</p>
        </div>
        <nav className="space-y-2">
          <NavItem to="/" icon={BarChart3} label="概览" />
          <NavItem to="/screener" icon={List} label="候选股票池" />
          <NavItem to="/history" icon={History} label="历史存档" />
          <NavItem to="/logs" icon={Activity} label="运行日志" />
          <NavItem to="/advisor" icon={MessageCircle} label="AI 顾问" />
        </nav>
      </aside>

      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
