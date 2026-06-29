import { motion } from 'framer-motion'
import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchLatestSnapshot,
  fetchLogs,
  runPipeline,
  getWatchlistDownloadUrl,
} from '../services/api'
import {
  TrendingUp,
  PieChart,
  Calendar,
  RefreshCw,
  Download,
  ArrowRight,
  Activity,
} from 'lucide-react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0 },
}

function StatCard({
  label,
  value,
  subtext,
  icon: Icon,
}: {
  label: string
  value: string
  subtext?: string
  icon: React.ElementType
}) {
  return (
    <motion.div
      variants={itemVariants}
      className="glass-card rounded-2xl p-6 relative overflow-hidden group"
    >
      <div className="absolute top-0 right-0 p-4 opacity-30 group-hover:opacity-50 transition-opacity duration-500">
        <Icon size={20} strokeWidth={1.5} />
      </div>
      <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-3">{label}</p>
      <p className="font-serif text-3xl text-sumi">{value}</p>
      {subtext && (
        <p className="text-xs text-ink-500 mt-2">{subtext}</p>
      )}
    </motion.div>
  )
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-12 text-ink-500">{label}</span>
      <div className="flex-1 h-1.5 bg-ink-200/50 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1, delay: 0.3 }}
          className="h-full rounded-full bg-gradient-to-r from-moss to-moss/70"
        />
      </div>
      <span className="w-10 text-right font-mono text-ink-600">{value.toFixed(3)}</span>
    </div>
  )
}

export default function Overview() {
  const [snapshot, setSnapshot] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    const [snap, logList] = await Promise.all([
      fetchLatestSnapshot(),
      fetchLogs(),
    ])
    setSnapshot(snap)
    setLogs(logList)
  }

  async function handleRun() {
    setLoading(true)
    await runPipeline()
    await loadData()
    setLoading(false)
  }

  const topStocks = snapshot?.items?.slice(0, 8) || []
  const latestLog = logs[0]

  const industryDistribution = useMemo(() => {
    const counts: Record<string, number> = {}
    snapshot?.items?.forEach((item: any) => {
      const industry = item.industry || '未分类'
      counts[industry] = (counts[industry] || 0) + 1
    })
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  }, [snapshot])

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      {/* Header */}
      <motion.div variants={itemVariants} className="flex items-end justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">
            Dashboard
          </p>
          <h2 className="font-serif text-4xl text-sumi">系统概览</h2>
        </div>
        <div className="flex gap-3">
          <motion.a
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            href={getWatchlistDownloadUrl()}
            download
            className="btn-secondary inline-flex items-center gap-2"
          >
            <Download size={14} strokeWidth={1.5} />
            导出 Watchlist
          </motion.a>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleRun}
            disabled={loading}
            className="btn-primary inline-flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw size={14} strokeWidth={1.5} className={loading ? 'animate-spin' : ''} />
            {loading ? '运行中' : '运行选股'}
          </motion.button>
        </div>
      </motion.div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          label="最新快照"
          value={snapshot?.date || '—'}
          icon={Calendar}
        />
        <StatCard
          label="候选股票"
          value={snapshot?.count?.toString() || '0'}
          subtext="通过所有及格线"
          icon={PieChart}
        />
        <StatCard
          label="当前最高分"
          value={snapshot?.items?.[0]?.total_score?.toFixed(3) || '—'}
          subtext={snapshot?.items?.[0]?.name}
          icon={TrendingUp}
        />
        <StatCard
          label="最近更新"
          value={latestLog?.status === 'success' ? '成功' : latestLog?.status || '—'}
          subtext={latestLog ? new Date(latestLog.time).toLocaleString('zh-CN') : undefined}
          icon={Activity}
        />
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Stocks */}
        <motion.div variants={itemVariants} className="lg:col-span-2 glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase">Top Rankings</p>
              <h3 className="font-serif text-xl text-sumi mt-1">今日优选</h3>
            </div>
            <Link
              to="/screener"
              className="text-xs text-ink-500 hover:text-sumi flex items-center gap-1 transition-colors"
            >
              查看全部
              <ArrowRight size={12} />
            </Link>
          </div>

          <div className="space-y-4">
            {topStocks.map((item: any, index: number) => (
              <Link
                key={item.symbol}
                to={`/stock/${item.symbol}`}
                className="block group"
              >
                <div className="flex items-center gap-4 p-4 rounded-xl border border-transparent hover:border-ink-200/60 hover:bg-ink-100/30 transition-all duration-300"
                >
                  <span className="font-serif text-2xl text-ink-300 w-8">
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <span className="font-medium text-sumi">{item.name}</span>
                      <span className="font-mono text-xs text-ink-500">{item.symbol}</span>
                      <span className="text-[10px] px-2 py-0.5 rounded-full bg-ink-100 text-ink-600">
                        {item.industry || '未分类'}
                      </span>
                    </div>
                    <div className="mt-2">
                      <ScoreBar label="综合" value={item.total_score} />
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="font-serif text-2xl text-moss">{item.total_score.toFixed(3)}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </motion.div>

        {/* Sidebar */}
        <div className="space-y-6">
          <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
            <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-4">
              Score Breakdown
            </p>
            {topStocks[0] && (
              <div className="space-y-4">
                <div className="pb-4 border-b border-ink-200/40">
                  <p className="text-xs text-ink-500">榜首</p>
                  <p className="font-serif text-2xl text-sumi">{topStocks[0].name}</p>
                </div>
                <ScoreBar label="质量" value={topStocks[0].quality_score} />
                <ScoreBar label="估值" value={topStocks[0].value_score} />
                <ScoreBar label="动量" value={topStocks[0].momentum_score} />
              </div>
            )}
          </motion.div>

          <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
            <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-4">
              Industry Distribution
            </p>
            {industryDistribution.length > 0 ? (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={industryDistribution} layout="vertical" margin={{ left: 40, right: 20, top: 5, bottom: 5 }}>
                    <XAxis type="number" hide />
                    <YAxis
                      dataKey="name"
                      type="category"
                      tick={{ fill: '#6e665c', fontSize: 11 }}
                      width={60}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      cursor={{ fill: 'rgba(107, 123, 95, 0.05)' }}
                      contentStyle={{
                        background: 'rgba(255, 255, 255, 0.9)',
                        border: '1px solid rgba(44, 42, 38, 0.08)',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={16}>
                      {industryDistribution.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={index === 0 ? '#6b7b5f' : '#b8b5ad'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-sm text-ink-500">暂无数据</p>
            )}
          </motion.div>

          <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
            <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-4">
              System Status
            </p>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-ink-500">数据源</span>
                <span className="text-sumi">AkShare / Mock</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-500">定时任务</span>
                <span className="text-sumi">每日 19:00</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-500">过滤策略</span>
                <span className="text-sumi">行业差异化</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
