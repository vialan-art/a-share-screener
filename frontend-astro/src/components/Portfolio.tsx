import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { fetchPortfolio, fetchPortfolioNav } from '../services/api'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import { Wallet, TrendingUp, PieChart } from 'lucide-react'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

interface PortfolioItem {
  symbol: string
  name: string
  industry: string
  total_score: number
  weight: number
}

interface NavRecord {
  date: string
  portfolio_return: number
  benchmark_return: number
  daily_return: number
  benchmark_daily_return: number
}

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState<{ date: string; items: PortfolioItem[] } | null>(null)
  const [nav, setNav] = useState<NavRecord[]>([])

  useEffect(() => {
    fetchPortfolio().then(setPortfolio)
    fetchPortfolioNav().then((data) => setNav(data || []))
  }, [])

  const chartData = useMemo(() => {
    return nav.map((r) => ({
      date: r.date,
      组合: Math.round(r.portfolio_return * 100) / 100,
      沪深300: Math.round(r.benchmark_return * 100) / 100,
    }))
  }, [nav])

  const latestNav = nav[nav.length - 1]
  const excess = latestNav ? latestNav.portfolio_return - latestNav.benchmark_return : null

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">Portfolio</p>
        <h2 className="font-serif text-4xl text-sumi">实盘组合</h2>
        <p className="text-sm text-ink-500 mt-2">
          每日选股流程自动保存的 Top 20 等权组合，用于真实跟踪策略表现
        </p>
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <Wallet size={14} className="text-ink-400" />
            <p className="text-[10px] tracking-widest text-ink-500 uppercase">最新组合日期</p>
          </div>
          <p className="font-serif text-2xl text-sumi">{portfolio?.date || '—'}</p>
          <p className="text-xs text-ink-400 mt-1">{portfolio ? `${portfolio.items.length} 只等权配置` : '暂无组合'}</p>
        </div>

        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} className="text-ink-400" />
            <p className="text-[10px] tracking-widest text-ink-500 uppercase">组合累计收益</p>
          </div>
          <p
            className={`font-serif text-2xl ${
              latestNav && latestNav.portfolio_return >= 0 ? 'text-moss' : 'text-rose-600'
            }`}
          >
            {latestNav ? `${latestNav.portfolio_return > 0 ? '+' : ''}${latestNav.portfolio_return.toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-ink-400 mt-1">自组合成立日起</p>
        </div>

        <div className="glass-card rounded-xl p-5">
          <div className="flex items-center gap-2 mb-2">
            <PieChart size={14} className="text-ink-400" />
            <p className="text-[10px] tracking-widest text-ink-500 uppercase">相对沪深300超额</p>
          </div>
          <p
            className={`font-serif text-2xl ${
              excess && excess >= 0 ? 'text-moss' : 'text-rose-600'
            }`}
          >
            {excess !== null ? `${excess > 0 ? '+' : ''}${excess.toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-ink-400 mt-1">基准：{latestNav ? `${latestNav.benchmark_return.toFixed(2)}%` : '—'}</p>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
        <h3 className="font-medium text-sumi mb-6">累计净值对比</h3>
        <div className="h-72">
          {chartData.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.05)" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#9ca3af" />
                <YAxis tick={{ fontSize: 11 }} stroke="#9ca3af" unit="%" />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.08)' }}
                  formatter={(v: number) => [`${v.toFixed(2)}%`, '']}
                />
                <Legend />
                <Line type="monotone" dataKey="组合" stroke="#4a6c4b" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="沪深300" stroke="#d97706" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-sm text-ink-500 text-center py-24">净值数据不足，需运行至少两个交易日</p>
          )}
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="elegant-table">
            <thead>
              <tr className="bg-ink-100/40">
                <th className="px-6 py-4 text-left">排名</th>
                <th className="px-6 py-4 text-left">股票</th>
                <th className="px-6 py-4 text-left">行业</th>
                <th className="px-6 py-4 text-right">综合得分</th>
                <th className="px-6 py-4 text-right">权重</th>
              </tr>
            </thead>
            <tbody>
              {portfolio?.items.map((item, index) => (
                <tr key={item.symbol} className="group">
                  <td className="px-6 py-4">
                    <span className="font-serif text-lg text-ink-300">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <a
                      href={`/stock/?symbol=${item.symbol}`}
                      className="block hover:text-moss transition-colors"
                    >
                      <span className="font-medium text-sumi">{item.name}</span>
                      <span className="block font-mono text-[10px] text-ink-400 mt-0.5">
                        {item.symbol}
                      </span>
                    </a>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-ink-100/70 text-ink-600 whitespace-nowrap">
                      {item.industry || '未分类'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.total_score.toFixed(3)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {(item.weight * 100).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
