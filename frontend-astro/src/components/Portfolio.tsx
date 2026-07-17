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
import DissolveCard from '../components/DissolveCard'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.08 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

function SectionHeader({ number, label, title }: { number: string; label: string; title: string }) {
  return (
    <div className="mb-6">
      <p className="editorial-label mb-3">( {number} ) · {label}</p>
      <h2 className="font-display text-4xl lg:text-5xl text-slate-50">{title}</h2>
    </div>
  )
}

interface PortfolioItem {
  symbol: string
  name: string
  industry: string
  total_score: number
  weight: number
  change_pct?: number | null
  latest_price?: number | null
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
      className="space-y-8 pb-12"
    >
      <motion.div variants={itemVariants}>
        <SectionHeader number="02" label="Portfolio" title="实盘组合" />
        <p className="text-sm text-slate-500 -mt-4">
          每日选股流程自动保存的 Top 20 等权组合，用于真实跟踪策略表现
        </p>
      </motion.div>

      <motion.div variants={itemVariants} className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <DissolveCard className="liquid-glass p-6">
          <div className="flex items-center gap-2 mb-3">
            <Wallet size={14} className="text-slate-400" />
            <p className="editorial-label">最新组合日期</p>
          </div>
          <p className="font-display text-3xl text-slate-50">{portfolio?.date || '—'}</p>
          <p className="text-xs text-slate-400 mt-1">{portfolio ? `${portfolio.items.length} 只等权配置` : '暂无组合'}</p>
        </DissolveCard>

        <DissolveCard className="liquid-glass p-6">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={14} className="text-slate-400" />
            <p className="editorial-label">组合累计收益</p>
          </div>
          <p
            className={`font-display text-3xl ${
              latestNav && latestNav.portfolio_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'
            }`}
          >
            {latestNav ? `${latestNav.portfolio_return > 0 ? '+' : ''}${latestNav.portfolio_return.toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-slate-400 mt-1">自组合成立日起</p>
        </DissolveCard>

        <DissolveCard className="liquid-glass p-6">
          <div className="flex items-center gap-2 mb-3">
            <PieChart size={14} className="text-slate-400" />
            <p className="editorial-label">相对沪深300超额</p>
          </div>
          <p
            className={`font-display text-3xl ${
              excess && excess >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'
            }`}
          >
            {excess !== null ? `${excess > 0 ? '+' : ''}${excess.toFixed(2)}%` : '—'}
          </p>
          <p className="text-xs text-slate-400 mt-1">基准：{latestNav ? `${latestNav.benchmark_return.toFixed(2)}%` : '—'}</p>
        </DissolveCard>
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="liquid-glass p-6 lg:p-8">
          <h3 className="font-display text-xl text-slate-50 mb-6">累计净值对比</h3>
          <div className="h-72">
            {chartData.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(90,90,106,0.15)" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="#94a3b8" />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} stroke="#94a3b8" unit="%" />
                  <Tooltip
                    contentStyle={{
                      borderRadius: '12px',
                      border: '1px solid rgba(37,37,50,0.6)',
                      boxShadow: '0 4px 20px rgba(0,0,0,0.35)',
                      background: 'rgba(22,22,29,0.92)',
                      backdropFilter: 'blur(12px)',
                      color: '#f0f4f8',
                    }}
                    formatter={(v: number) => [`${v.toFixed(2)}%`, '']}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="组合" stroke="#38bdf8" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="沪深300" stroke="#f0abfc" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm text-slate-500 text-center py-24">净值数据不足，需运行至少两个交易日</p>
            )}
          </div>
        </DissolveCard>
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="liquid-glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="elegant-table">
              <thead>
                <tr className="bg-slate-800/30">
                  <th className="px-6 py-4 text-left">排名</th>
                  <th className="px-6 py-4 text-left">股票</th>
                  <th className="px-6 py-4 text-left">行业</th>
                  <th className="px-6 py-4 text-right">最新价</th>
                  <th className="px-6 py-4 text-right">今日涨跌</th>
                  <th className="px-6 py-4 text-right">综合得分</th>
                  <th className="px-6 py-4 text-right">权重</th>
                </tr>
              </thead>
              <tbody>
                {portfolio?.items.map((item, index) => (
                  <tr key={item.symbol} className="group">
                    <td className="px-6 py-4">
                      <span className="font-display text-xl text-slate-200 italic">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <a
                        href={`/stock/?symbol=${item.symbol}`}
                        className="block hover:text-cyan-300 transition-colors"
                      >
                        <span className="font-medium text-slate-50">{item.name}</span>
                        <span className="block font-mono text-[10px] text-slate-400 mt-0.5">
                          {item.symbol}
                        </span>
                      </a>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-[10px] tracking-wide px-2.5 py-1 rounded-full glass-float text-slate-600 whitespace-nowrap">
                        {item.industry || '未分类'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">
                      {item.latest_price ? `¥${item.latest_price.toFixed(2)}` : '—'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      {item.change_pct !== null && item.change_pct !== undefined ? (
                        <span className={`font-mono text-sm font-medium ${item.change_pct >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'}`}>
                          {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-slate-700 text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">
                      {item.total_score.toFixed(3)}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">
                      {(item.weight * 100).toFixed(2)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </DissolveCard>
      </motion.div>
    </motion.div>
  )
}
