import { motion } from 'framer-motion'
import { useEffect, useState, useMemo } from 'react'
import {
  fetchLatestSnapshot,
  fetchLogs,
  fetchQualitySummary,
  fetchQualityDetail,
  runPipeline,
  fetchRunStatus,
  fetchBacktest,
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
  ShieldAlert,
  Database,
  CheckCircle2,
  AlertCircle,
  History,
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

function CoverageBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-20 text-ink-500">{label}</span>
      <div className="flex-1 h-1.5 bg-ink-200/50 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${pct >= 70 ? 'bg-moss' : pct >= 40 ? 'bg-amber-500' : 'bg-rust'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right font-mono text-ink-600">{pct}%</span>
    </div>
  )
}

export default function Overview() {
  const [snapshot, setSnapshot] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [quality, setQuality] = useState<any>(null)
  const [qualityDetail, setQualityDetail] = useState<any>(null)
  const [backtest, setBacktest] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [runProgress, setRunProgress] = useState<string | null>(null)
  const [runError, setRunError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    const [snap, logList, qualityData, qualityDetailData, backtestData] = await Promise.all([
      fetchLatestSnapshot(),
      fetchLogs(),
      fetchQualitySummary(),
      fetchQualityDetail(),
      fetchBacktest(),
    ])
    setSnapshot(snap)
    setLogs(logList)
    setQuality(qualityData)
    setQualityDetail(qualityDetailData)
    setBacktest(backtestData)
  }

  async function handleRun() {
    setLoading(true)
    setRunError(null)
    setRunProgress(null)
    try {
      const { job_id } = await runPipeline()
      pollJob(job_id)
    } catch (e: any) {
      setRunError(e.message || '启动失败')
      setLoading(false)
    }
  }

  async function pollJob(jobId: string) {
    const interval = setInterval(async () => {
      try {
        const status = await fetchRunStatus(jobId)
        setRunProgress(status.progress || status.status)
        if (status.status === 'success' || status.status === 'failed') {
          clearInterval(interval)
          setLoading(false)
          if (status.status === 'failed') {
            setRunError(status.error || '运行失败')
          } else {
            setRunProgress('完成')
            await loadData()
          }
        }
      } catch (e: any) {
        clearInterval(interval)
        setRunError(e.message || '查询状态失败')
        setLoading(false)
      }
    }, 2000)
  }

  const topStocks = snapshot?.items?.slice(0, 8) || []
  const latestLog = logs[0]
  const meta = snapshot?.meta || {}
  const providerName = latestLog?.provider || 'mock'
  const providerLabel = providerName === 'akshare' ? 'AkShare（真实 A 股）' : 'Mock（模拟数据）'
  const completenessPct = quality?.avg_completeness
    ? Math.round(quality.avg_completeness * 100)
    : latestLog?.completeness_avg
    ? Math.round(latestLog.completeness_avg * 100)
    : null

  const industryDistribution = useMemo(() => {
    const counts: Record<string, number> = meta.industry_distribution || {}
    // 如果 API 没返回分布，再自己算
    if (Object.keys(counts).length === 0) {
      snapshot?.items?.forEach((item: any) => {
        const industry = item.industry || '未分类'
        counts[industry] = (counts[industry] || 0) + 1
      })
    }
    return Object.entries(counts)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
  }, [snapshot, meta])

  const backtestResults = backtest?.results || []

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
          <h2 className="font-display text-4xl text-sumi">系统概览</h2>
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
            {loading ? (runProgress || '运行中') : '运行选股'}
          </motion.button>
        </div>
      </motion.div>

      {runError && (
        <motion.div
          variants={itemVariants}
          className="marble-card rounded-2xl p-4 border-rust/30 bg-rust/5"
        >
          <p className="text-xs text-rust font-medium">运行失败</p>
          <p className="text-xs text-rust/80 mt-1">{runError}</p>
        </motion.div>
      )}

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
          subtext={meta.avg_score !== null && meta.avg_score !== undefined ? `平均分 ${meta.avg_score.toFixed(3)}` : '通过所有及格线'}
          icon={PieChart}
        />
        <StatCard
          label="当前最高分"
          value={snapshot?.items?.[0]?.total_score?.toFixed(3) || '—'}
          subtext={snapshot?.items?.[0]?.name}
          icon={TrendingUp}
        />
        <StatCard
          label="数据完整度"
          value={completenessPct !== null ? `${completenessPct}%` : '—'}
          subtext={providerLabel}
          icon={Activity}
        />
      </div>

      {/* Disclaimer */}
      <motion.div
        variants={itemVariants}
        className="marble-card rounded-2xl p-5 border-amber-200/50"
      >
        <div className="flex items-start gap-3">
          <ShieldAlert size={18} className="text-amber-600 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-amber-800 mb-1">数据免责声明</p>
            <p className="text-xs text-amber-700/80 leading-relaxed">
              本页面所有财务和行情数据均来自第三方公开接口（AkShare / Mock 模拟数据）。
              我们已加入数据质量校验，但无法保证 100% 正确，可能存在延迟、字段缺失或接口变更导致的错误。
              本站仅供学习研究，不构成任何投资建议。
            </p>
          </div>
        </div>
      </motion.div>

      {/* Backtest Preview */}
      {backtestResults.length > 0 && (
        <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <History size={18} className="text-moss" />
            <div>
              <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase">Strategy Backtest</p>
              <h3 className="font-display text-xl text-sumi mt-1">策略历史表现（等权重 Top 20）</h3>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {backtestResults.map((r: any) => {
              const hasError = r.error || r.portfolio_return === null
              const portfolioColor = r.portfolio_return > 0 ? 'text-moss' : r.portfolio_return < 0 ? 'text-rust' : 'text-ink-500'
              const benchmarkColor = r.benchmark_return > 0 ? 'text-moss' : r.benchmark_return < 0 ? 'text-rust' : 'text-ink-500'
              return (
                <div key={r.label} className="p-4 rounded-xl border border-ink-200/40 bg-washi/30">
                  <p className="text-xs text-ink-500 mb-2">{r.label} 买入持有至今</p>
                  {hasError ? (
                    <p className="text-xs text-amber-600">{r.error || '缺少历史价格数据'}</p>
                  ) : (
                    <>
                      <p className={`font-serif text-2xl ${portfolioColor}`}>
                        {r.portfolio_return > 0 ? '+' : ''}{r.portfolio_return}%
                      </p>
                      <p className="text-xs text-ink-500 mt-1">
                        沪深300: <span className={benchmarkColor}>{r.benchmark_return > 0 ? '+' : ''}{r.benchmark_return}%</span>
                        {' · '}
                        超额: <span className={r.excess_return > 0 ? 'text-moss' : 'text-rust'}>{r.excess_return > 0 ? '+' : ''}{r.excess_return}%</span>
                      </p>
                      <div className="flex items-center gap-3 mt-2 text-[10px] text-ink-400">
                        <span>年化 {r.annualized_return > 0 ? '+' : ''}{r.annualized_return}%</span>
                        <span>最大回撤 {r.max_drawdown}%</span>
                        <span>胜率 {r.win_rate}%</span>
                      </div>
                      <p className="text-[10px] text-ink-400 mt-1">有效股票 {r.valid_stocks}/{r.top_n}</p>
                    </>
                  )}
                </div>
              )
            })}
          </div>
          <p className="text-[10px] text-ink-400 mt-4 leading-relaxed">
            说明：基于历史快照选股，等权重买入后持有至今，价格已做后复权处理。此回测仅用于验证策略是否有明显缺陷，不代表未来收益。
          </p>
        </motion.div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Stocks */}
        <motion.div variants={itemVariants} className="lg:col-span-2 glass-card rounded-2xl p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase">Top Rankings</p>
              <h3 className="font-display text-xl text-sumi mt-1">今日优选</h3>
            </div>
            <a
              href="/screener/"
              className="text-xs text-ink-500 hover:text-sumi flex items-center gap-1 transition-colors"
            >
              查看全部
              <ArrowRight size={12} />
            </a>
          </div>

          <div className="space-y-4">
            {topStocks.map((item: any, index: number) => (
              <a
                key={item.symbol}
                href={`/stock/?symbol=${item.symbol}`}
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
              </a>
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
              Data Quality
            </p>
            <div className="space-y-3">
              <CoverageBar label="最新价" value={qualityDetail?.field_coverage?.latest_price} />
              <CoverageBar label="PE TTM" value={qualityDetail?.field_coverage?.pe_ttm} />
              <CoverageBar label="PB" value={qualityDetail?.field_coverage?.pb} />
              <CoverageBar label="ROE" value={qualityDetail?.field_coverage?.roe} />
              <CoverageBar label="净利润" value={qualityDetail?.field_coverage?.net_profit} />
              <CoverageBar label="净利润增长" value={qualityDetail?.field_coverage?.profit_growth} />
              <CoverageBar label="资产负债率" value={qualityDetail?.field_coverage?.debt_to_asset} />
              <CoverageBar label="经营现金流" value={qualityDetail?.field_coverage?.operating_cash_flow} />
              <CoverageBar label="股息率" value={qualityDetail?.field_coverage?.dividend_yield} />
            </div>
            <div className="mt-4 pt-4 border-t border-ink-200/40 flex items-center gap-2 text-xs text-ink-500">
              {qualityDetail?.total ? (
                <>
                  <Database size={12} />
                  共 {qualityDetail.total} 条财务记录
                </>
              ) : (
                <span>暂无数据</span>
              )}
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
            <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-4">
              Recent Updates
            </p>
            <div className="space-y-3">
              {(qualityDetail?.recent_logs || []).slice(0, 5).map((log: any, idx: number) => (
                <div key={idx} className="flex items-start gap-2 text-xs">
                  {log.status === 'success' ? (
                    <CheckCircle2 size={12} className="text-moss mt-0.5 shrink-0" />
                  ) : (
                    <AlertCircle size={12} className="text-amber-600 mt-0.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sumi truncate">{log.message}</p>
                    <p className="text-ink-500 mt-0.5">
                      {new Date(log.time).toLocaleString('zh-CN')} · {log.provider || 'unknown'} · {log.stocks_count ?? '—'} 只
                    </p>
                  </div>
                </div>
              ))}
              {(qualityDetail?.recent_logs || []).length === 0 && (
                <p className="text-sm text-ink-500">暂无更新记录</p>
              )}
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
            <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-4">
              System Status
            </p>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-ink-500">数据源</span>
                  <span className="text-sumi flex items-center gap-1.5">
                    <Database size={12} className="text-ink-400" />
                    {providerLabel}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-500">定时任务</span>
                  <span className="text-sumi">每日 19:00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-500">覆盖股票</span>
                  <span className="text-sumi">{latestLog?.stocks_count ? `${latestLog.stocks_count} 只` : '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-500">过滤策略</span>
                  <span className="text-sumi">行业差异化</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-500">数据可信度</span>
                  <span className={`text-xs ${completenessPct && completenessPct >= 70 ? 'text-moss' : completenessPct && completenessPct >= 40 ? 'text-amber-600' : 'text-rust'}`}>
                    {completenessPct !== null ? `${completenessPct}% 完整度` : '未知'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-ink-500">最近更新</span>
                  <span className="text-xs text-ink-600">
                    {latestLog ? new Date(latestLog.time).toLocaleString('zh-CN') : '—'}
                  </span>
                </div>
              </div>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
