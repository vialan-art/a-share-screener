import { motion } from 'framer-motion'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  BarChart3,
  List,
  History,
  MessageCircle,
  Activity,
  Telescope,
  Sparkles,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: BarChart3, label: '概览', labelEn: 'Overview' },
  { to: '/screener', icon: Telescope, label: '选股池', labelEn: 'Screener' },
  { to: '/history', icon: History, label: '历史', labelEn: 'History' },
  { to: '/logs', icon: Activity, label: '日志', labelEn: 'Logs' },
  { to: '/advisor', icon: Sparkles, label: 'Advisor', labelEn: 'AI' },
]

function NavItem({ to, icon: Icon, label, labelEn, isActive }: typeof navItems[0] & { isActive: boolean }) {
  return (
    <NavLink
      to={to}
      className={() =>
        `group relative flex items-center gap-4 px-5 py-4 rounded-xl transition-all duration-500 ${
          isActive
            ? 'bg-sumi text-ink-50 shadow-soft'
            : 'text-ink-500 hover:bg-ink-100/60 hover:text-sumi'
        }`
      }
    >
      <Icon
        size={18}
        strokeWidth={1.5}
        className="transition-transform duration-500 group-hover:scale-110"
      />
      <div className="flex flex-col">
        <span className="text-sm font-medium tracking-wide">{label}</span>
        <span className={`text-[10px] tracking-widest uppercase ${
          isActive ? 'text-ink-300' : 'text-ink-400'
        }`}>{labelEn}</span>
      </div>
      {isActive && (
        <motion.div
          layoutId="activeNav"
          className="absolute right-3 w-1.5 h-1.5 rounded-full bg-moss"
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        />
      )}
    </NavLink>
  )
}

export default function Layout() {
  const location = useLocation()

  return (
    <div className="min-h-screen flex">
      <aside className="w-72 bg-white/60 backdrop-blur-2xl border-r border-ink-200/40 flex flex-col fixed h-full z-20">
        <div className="p-8 pb-6">
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="font-serif text-2xl font-semibold text-sumi tracking-wide">
              选股
            </h1>
            <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mt-1">
              A-Share Screener
            </p>
          </motion.div>
        </div>

        <nav className="flex-1 px-4 space-y-1">
          {navItems.map((item) => (
            <NavItem key={item.to} {...item} isActive={location.pathname === item.to} />
          ))}
        </nav>

        <div className="p-6 border-t border-ink-200/40">
          <div className="glass-card rounded-xl p-4">
            <p className="text-[10px] tracking-widest text-ink-500 uppercase mb-2">
              今日箴言
            </p>
            <p className="text-xs text-ink-700 leading-relaxed font-serif">
              "投资最重要的是不要亏钱，第二重要的是记住第一条。"
            </p>
            <p className="text-[10px] text-ink-400 mt-2 text-right">— Warren Buffett</p>
          </div>
        </div>
      </aside>

      <main className="flex-1 ml-72 min-h-screen">
        <motion.div
          key={location.pathname}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="p-8 lg:p-12 max-w-7xl mx-auto"
        >
          <Outlet />
        </motion.div>
      </main>
    </div>
  )
}
