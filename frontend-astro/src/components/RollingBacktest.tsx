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

const containerVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
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
        ? 'text-moss'
        : 'text-rose-600'
      : isPositive
        ? 'text-rose-600'
        : 'text-moss'
  return (
    <div className="glass-card rounded-xl p-4">
      <p className="text-[10px] tracking-widest text-ink-500 uppercase mb-1">{label}</p>
      <p className={`font-serif text-2xl ${colorClass}`}>
        {value > 0 ? '+' : ''}
        {value.toFixed(2)}
        {suffix}
      </p>
    </div>
  )
}

export default function RollingBacktest() {
  const [data, setData] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)
  const [topN, setTopN] = useState(20)

  const [frequency, setFrequency] = useState('daily')

  async function load() {
    setLoading(true)
    const res = await fetchRollingBacktest({ top_n: topN, frequency })
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
      className="space-y-6"
    >
      <motion.div variants={itemVariants} className="flex items-end justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">Backtest</p>
          <h2 className="font-serif text-4xl text-sumi">滚动回测</h2>
          <p className="text-sm text-ink-500 mt-2">
            按所选频率调仓，等权持有 Top N，对比沪深300与随机选股
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="relative">
            <TrendingUp size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
            <select
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value))}
              className="pl-9 pr-8 py-2.5 bg-ink-50 border border-ink-200/60 rounded-lg text-sm text-sumi focus:outline-none focus:border-moss/50 appearance-none min-w-[100px]"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
          </div>
          <div className="relative">
            <Calendar size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="pl-9 pr-8 py-2.5 bg-ink-50 border border-ink-200/60 rounded-lg text-sm text-sumi focus:outline-none focus:border-moss/50 appearance-none min-w-[120px]"
            >
              <option value="auto">自动</option>
              <option value="monthly">月度</option>
              <option value="weekly">周度</option>
              <option value="daily">日度</option>
            </select>
          </div>
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
        <motion.div variants={itemVariants} className="glass-card rounded-2xl p-8 text-center text-ink-500">
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
            <div className="lg:col-span-2 glass-card rounded-2xl p-6">
              <div className="flex items-center gap-2 mb-6">
                <Activity size={16} className="text-ink-400" />
                <h3 className="font-medium text-sumi">净值走势</h3>
              </div>
              <div className="h-80">
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
                    <Line type="monotone" dataKey="策略" stroke="#4a6c4b" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="随机" stroke="#9ca3af" strokeWidth={2} dot={false} strokeDasharray="4 4" />
                    <Line type="monotone" dataKey="沪深300" stroke="#d97706" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="glass-card rounded-2xl p-6 space-y-6">
              <div>
                <p className="text-[10px] tracking-widest text-ink-500 uppercase mb-3">对比摘要</p>
                <div className="space-y-3">
                  <div className="flex justify-between text-sm">
                    <span className="text-ink-500">策略 / 随机 / 基准</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-sumi">累计收益</span>
                    <span className="font-mono">
                      {data.strategy.total_return}% / {data.random.total_return}% / {data.benchmark.total_return}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-sumi">年化收益</span>
                    <span className="font-mono">
                      {data.strategy.annualized_return}% / {data.random.annualized_return}% / {data.benchmark.annualized_return}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-sumi">最大回撤</span>
                    <span className="font-mono">
                      {data.strategy.max_drawdown}% / {data.random.max_drawdown}% / {data.benchmark.max_drawdown}%
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-sumi">胜率</span>
                    <span className="font-mono">
                      {data.strategy.win_rate}% / {data.random.win_rate}% / —
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <p className="text-[10px] tracking-widest text-ink-500 uppercase mb-3">回测区间</p>
                <div className="flex items-center gap-2 text-sm text-ink-600">
                  <Calendar size={14} />
                  <span>
                    {data.start_date} 至 {data.end_date}
                  </span>
                </div>
                <p className="text-xs text-ink-400 mt-2">
                  共 {data.periods} 个调仓周期，Top {data.top_n} 等权
                  {data.frequency && (
              <span className="ml-2">· 频率: {data.frequency}</span>
            )}
            {data.end_date !== data.start_date && (
              <span className="ml-2">· 实际可用数据至 {data.end_date}</span>
            )}
                </p>
              </div>
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="glass-card rounded-2xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="elegant-table">
                <thead>
                  <tr className="bg-ink-100/40">
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
                      <td className="px-6 py-4 font-mono text-sm text-ink-600">
                        {r.start_date} → {r.end_date}
                      </td>
                      <td
                        className={`px-6 py-4 text-right font-mono text-sm ${
                          r.strategy_return >= 0 ? 'text-moss' : 'text-rose-600'
                        }`}
                      >
                        {r.strategy_return > 0 ? '+' : ''}
                        {r.strategy_return}%
                      </td>
                      <td
                        className={`px-6 py-4 text-right font-mono text-sm ${
                          r.random_return >= 0 ? 'text-moss' : 'text-rose-600'
                        }`}
                      >
                        {r.random_return > 0 ? '+' : ''}
                        {r.random_return}%
                      </td>
                      <td
                        className={`px-6 py-4 text-right font-mono text-sm ${
                          r.benchmark_return >= 0 ? 'text-moss' : 'text-rose-600'
                        }`}
                      >
                        {r.benchmark_return > 0 ? '+' : ''}
                        {r.benchmark_return}%
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-ink-500">
                        {r.valid_stocks} / {r.valid_stocks + r.missing_stocks}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        </>
      ) : null}
    </motion.div>
  )
}
