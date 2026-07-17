import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { fetchRollingBacktest } from '../services/api'
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
import { TrendingUp, Activity, Calendar } from 'lucide-react'
import DissolveCard from '../components/DissolveCard'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
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

interface Record {
  start_date: string
  end_date: string
  strategy_return: number
  random_return: number
  benchmark_return: number
  valid_stocks: number
  missing_stocks: number
}

interface Result {
  start_date: string
  end_date: string
  top_n: number
  periods: number
  strategy: {
    total_return: number
    annualized_return: number
    max_drawdown: number
    sharpe: number
    win_rate: number
  }
  random: {
    total_return: number
    annualized_return: number
    max_drawdown: number
    win_rate: number
  }
  benchmark: {
    total_return: number
    annualized_return: number
    max_drawdown: number
  }
  records: Record[]
  error?: string
}

function StatCard({
  label,
  value,
  suffix = '',
  positiveGood = true,
}: {
  label: string
  value: number | null
  suffix?: string
  positiveGood?: boolean
}) {
  if (value === null || value === undefined) return null
  const isPositive = value >= 0
  const colorClass =
    positiveGood || value === 0
      ? isPositive
        ? 'text-cyan-300'
        : 'text-fuchsia-300'
      : isPositive
        ? 'text-fuchsia-300'
        : 'text-cyan-300'
  return (
    <DissolveCard className="liquid-glass p-5">
      <p className="editorial-label mb-2">{label}</p>
      <p className={`font-display text-3xl ${colorClass}`}>
        {value > 0 ? '+' : ''}
        {value.toFixed(2)}
        {suffix}
      </p>
    </DissolveCard>
  )
}

export default function RollingBacktest() {
  const [data, setData] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)
  const [topN, setTopN] = useState(20)
  const [frequency, setFrequency] = useState('daily')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  async function load() {
    setLoading(true)
    const res = await fetchRollingBacktest({
      top_n: topN,
      frequency,
      start_date: startDate || undefined,
      end_date: endDate || undefined,
    })
    setData(res)
    setLoading(false)
  }

  useEffect(() => {
    load()
  }, [frequency])

  const chartData = useMemo(() => {
    if (!data?.records) return []
    let strategyNav = 1
    let randomNav = 1
    let benchmarkNav = 1
    return data.records.map((r) => {
      strategyNav *= 1 + r.strategy_return / 100
      randomNav *= 1 + r.random_return / 100
      benchmarkNav *= 1 + r.benchmark_return / 100
      return {
        date: r.end_date,
        策略: Math.round((strategyNav - 1) * 10000) / 100,
        随机: Math.round((randomNav - 1) * 10000) / 100,
        沪深300: Math.round((benchmarkNav - 1) * 10000) / 100,
      }
    })
  }, [data])

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 pb-12"
    >
      <motion.div variants={itemVariants} className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <SectionHeader number="02" label="Backtest" title="滚动回测" />

        <div className="flex items-center gap-3 flex-wrap">
          <div className="relative">
            <TrendingUp size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="glass-select min-w-[100px]"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
          </div>
          <div className="relative">
            <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="glass-select min-w-[120px]"
            >
              <option value="monthly">月度</option>
              <option value="weekly">周度</option>
              <option value="daily">日度</option>
            </select>
          </div>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="glass-select w-36 text-sm"
            placeholder="开始日期"
          />
          <span className="text-slate-600 text-xs">至</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="glass-select w-36 text-sm"
            placeholder="结束日期"
          />
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={load}
            disabled={loading}
            className="btn-primary disabled:opacity-50"
          >
            {loading ? '计算中...' : '运行回测'}
          </motion.button>
        </div>
      </motion.div>

      {data?.error ? (
        <motion.div variants={itemVariants} className="liquid-glass p-8 text-center text-slate-500">
          {data.error}
        </motion.div>
      ) : data ? (
        <>
          <motion.div variants={itemVariants} className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="策略累计收益" value={data.strategy.total_return} suffix="%" />
            <StatCard label="策略年化收益" value={data.strategy.annualized_return} suffix="%" />
            <StatCard label="策略最大回撤" value={-data.strategy.max_drawdown} suffix="%" positiveGood={false} />
            <StatCard label="策略胜率" value={data.strategy.win_rate} suffix="%" />
          </motion.div>

          <motion.div variants={itemVariants} className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <DissolveCard className="lg:col-span-2 liquid-glass p-6 lg:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 rounded-full liquid-glass flex items-center justify-center">
                  <Activity size={18} className="text-cyan-300" />
                </div>
                <h3 className="font-display text-xl text-slate-50">净值走势</h3>
              </div>
              <div className="h-80">
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
                    <Line type="monotone" dataKey="策略" stroke="#38bdf8" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="随机" stroke="#c4b5fd" strokeWidth={2} dot={false} strokeDasharray="4 4" />
                    <Line type="monotone" dataKey="沪深300" stroke="#f0abfc" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </DissolveCard>

            <DissolveCard className="liquid-glass p-6 space-y-6">
              <div>
                <p className="editorial-label mb-4">对比摘要</p>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">累计收益</span>
                    <span className="font-mono text-slate-50">
                      {data.strategy.total_return}% / {data.random.total_return}% / {data.benchmark.total_return}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">年化收益</span>
                    <span className="font-mono text-slate-50">
                      {data.strategy.annualized_return}% / {data.random.annualized_return}% / {data.benchmark.annualized_return}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">最大回撤</span>
                    <span className="font-mono text-slate-50">
                      {data.strategy.max_drawdown}% / {data.random.max_drawdown}% / {data.benchmark.max_drawdown}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-slate-500">胜率</span>
                    <span className="font-mono text-slate-50">
                      {data.strategy.win_rate}% / {data.random.win_rate}% / —
                    </span>
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-700">
                <p className="editorial-label mb-4">回测区间</p>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Calendar size={14} />
                  <span>
                    {data.start_date} 至 {data.end_date}
                  </span>
                </div>
                <p className="text-xs text-slate-400 mt-2">
                  共 {data.periods} 个调仓周期，Top {data.top_n} 等权
                  {data.frequency && <span className="ml-2">· 频率: {data.frequency}</span>}
                </p>
              </div>
            </DissolveCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <DissolveCard className="liquid-glass overflow-hidden">
              <div className="overflow-x-auto">
                <table className="elegant-table">
                  <thead>
                    <tr className="bg-slate-800/30">
                      <th className="px-6 py-4 text-left">调仓日</th>
                      <th className="px-6 py-4 text-right">策略收益</th>
                      <th className="px-6 py-4 text-right">随机收益</th>
                      <th className="px-6 py-4 text-right">沪深300</th>
                      <th className="px-6 py-4 text-right">有效标的</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.records.map((r) => (
                      <tr key={r.start_date} className="group">
                        <td className="px-6 py-4 font-mono text-sm text-slate-600">
                          {r.start_date} → {r.end_date}
                        </td>
                        <td
                          className={`px-6 py-4 text-right font-mono text-sm ${
                            r.strategy_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'
                          }`}
                        >
                          {r.strategy_return > 0 ? '+' : ''}
                          {r.strategy_return}%
                        </td>
                        <td
                          className={`px-6 py-4 text-right font-mono text-sm ${
                            r.random_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'
                          }`}
                        >
                          {r.random_return > 0 ? '+' : ''}
                          {r.random_return}%
                        </td>
                        <td
                          className={`px-6 py-4 text-right font-mono text-sm ${
                            r.benchmark_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'
                          }`}
                        >
                          {r.benchmark_return > 0 ? '+' : ''}
                          {r.benchmark_return}%
                        </td>
                        <td className="px-6 py-4 text-right font-mono text-sm text-slate-500">
                          {r.valid_stocks} / {r.valid_stocks + r.missing_stocks}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </DissolveCard>
          </motion.div>
        </>
      ) : null}
    </motion.div>
  )
}
