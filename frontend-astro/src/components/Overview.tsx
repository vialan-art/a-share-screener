import { motion } from 'framer-motion'
import { useEffect, useState, useMemo } from 'react'
import {
  fetchLatestSnapshot,
  fetchLogs,
  fetchQualitySummary,
  fetchQualityDetail,
  runPipeline,
  fetchRunStatus,
  fetchRollingBacktest,
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
import DissolveCard from '../components/DissolveCard'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
}

function SectionHeader({ number, label, title }: { number: string; label: string; title: string }) {
  return (
    <div className="mb-6">
      <p className="editorial-label mb-2">( {number} ) · {label}</p>
      <h2 className="font-display text-3xl lg:text-4xl text-slate-50">{title}</h2>
    </div>
  )
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
    <motion.div variants={itemVariants}>
      <DissolveCard className="glass-card rounded-2xl p-6 group hover:border-slate-600 transition-colors duration-300">
        <div className="flex items-center justify-between mb-4">
          <p className="editorial-label">{label}</p>
          <Icon size={18} className="text-slate-600 group-hover:text-slate-400 transition-colors" strokeWidth={1.5} />
        </div>
        <p className="font-display text-3xl text-slate-50">{value}</p>
        {subtext && <p className="text-xs text-slate-500 mt-2">{subtext}</p>}
      </DissolveCard>
    </motion.div>
  )
}

function ScoreBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-12 text-slate-500">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 1, delay: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="h-full rounded-full bg-cyan-400"
        />
      </div>
      <span className="w-10 text-right font-mono text-slate-400">{value.toFixed(3)}</span>
    </div>
  )
}

function CoverageBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round((value || 0) * 100)
  return (
    <div className="flex items-center gap-3 text-xs">
      <span className="w-20 text-slate-500">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${pct >= 70 ? 'bg-cyan-400' : pct >= 40 ? 'bg-cyan-400' : 'bg-fuchsia-400'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right font-mono text-slate-400">{pct}%</span>
    </div>
  )
}

function MiniStat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="glass-float rounded-xl p-4">
      <p className="editorial-label mb-2">{label}</p>
      {children}
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
      fetchRollingBacktest({ top_n: 20, frequency: 'daily' }),
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

  const backtestResult = backtest || null

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-12"
    >
      <motion.div variants={itemVariants} className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <SectionHeader number="01" label="Dashboard" title="系统概览" />
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
          className="glass-card rounded-2xl p-4"
        >
          <p className="text-xs text-fuchsia-300 font-medium">运行失败</p>
          <p className="text-xs text-fuchsia-300/80 mt-1">{runError}</p>
        </motion.div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="最新快照" value={snapshot?.date || '—'} icon={Calendar} />
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

      <motion.div
        variants={itemVariants}
        className="glass-card rounded-2xl p-5"
      >
        <div className="flex items-start gap-3">
          <ShieldAlert size={18} className="text-cyan-300 mt-0.5 shrink-0" />
          <div>
            <p className="text-xs font-medium text-slate-200 mb-1">数据免责声明</p>
            <p className="text-xs text-slate-500 leading-relaxed">
              本页面所有财务和行情数据均来自第三方公开接口（AkShare / Mock 模拟数据）。
              我们已加入数据质量校验，但无法保证 100% 正确，可能存在延迟、字段缺失或接口变更导致的错误。
              本站仅供学习研究，不构成任何投资建议。
            </p>
          </div>
        </div>
      </motion.div>

      {backtestResult && !backtestResult.error && (
        <motion.div variants={itemVariants}>
          <DissolveCard className="glass-card rounded-2xl p-6">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-6 gap-4">
              <div className="flex items-center gap-3">
                <History size={18} className="text-cyan-300" />
                <div>
                  <p className="editorial-label">Strategy Backtest</p>
                  <h3 className="font-display text-xl text-slate-50 mt-1">策略近期表现（滚动调仓 Top 20）</h3>
                </div>
              </div>
              <span className="text-[10px] tracking-[0.15em] uppercase px-3 py-1.5 rounded-lg glass-float text-slate-500">
                {backtestResult.periods} 个周期 · {backtestResult.frequency === 'daily' ? '日度' : backtestResult.frequency === 'weekly' ? '周度' : '月度'}
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MiniStat label="策略累计收益">
                <p className={`font-display text-2xl ${backtestResult.strategy?.total_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'}`}>
                  {backtestResult.strategy?.total_return > 0 ? '+' : ''}{backtestResult.strategy?.total_return}%
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  沪深300: <span className={backtestResult.benchmark?.total_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'}>{backtestResult.benchmark?.total_return > 0 ? '+' : ''}{backtestResult.benchmark?.total_return}%</span>
                </p>
              </MiniStat>
              <MiniStat label="最大回撤 / 胜率">
                <p className="font-display text-2xl text-slate-50">
                  {backtestResult.strategy?.max_drawdown}% / {backtestResult.strategy?.win_rate}%
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  {backtestResult.start_date} 至 {backtestResult.end_date}
                </p>
              </MiniStat>
              <MiniStat label="随机对照组">
                <p className={`font-display text-2xl ${backtestResult.random?.total_return >= 0 ? 'text-cyan-300' : 'text-fuchsia-300'}`}>
                  {backtestResult.random?.total_return > 0 ? '+' : ''}{backtestResult.random?.total_return}%
                </p>
                <p className="text-xs text-slate-500 mt-1">同池随机选股收益</p>
              </MiniStat>
            </div>
            <p className="text-[10px] text-slate-600 mt-5 leading-relaxed">
              说明：基于历史快照逐日调仓，等权重买入 Top 20，价格已做后复权处理。由于当前仅积累了 {backtestResult.periods} 个交易日的快照，此回测仅反映极短期表现，不能代表策略长期有效性。
            </p>
          </DissolveCard>
        </motion.div>
      )}

      {backtestResult?.error && (
        <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-4">
            <History size={18} className="text-cyan-300" />
            <h3 className="font-display text-xl text-slate-50">策略近期表现（滚动调仓 Top 20）</h3>
          </div>
          <p className="text-sm text-slate-500">{backtestResult.error}，需要更多历史快照才能生成有效回测。</p>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <motion.div variants={itemVariants} className="lg:col-span-2">
          <DissolveCard className="glass-card rounded-2xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <p className="editorial-label mb-2">Top Rankings</p>
                <h3 className="font-display text-xl text-slate-50">今日优选</h3>
              </div>
              <a
                href="/screener/"
                className="text-xs text-slate-500 hover:text-slate-50 flex items-center gap-1 transition-colors px-3 py-1.5 rounded-lg glass-float group"
              >
                查看全部
                <ArrowRight size={12} className="group-hover:translate-x-0.5 transition-transform" />
              </a>
            </div>

            <div className="space-y-1">
              {topStocks.map((item: any, index: number) => (
                <a
                  key={item.symbol}
                  href={`/stock/?symbol=${item.symbol}`}
                  className="block group"
                >
                  <div className="flex items-center gap-4 p-4 rounded-xl border border-transparent hover:border-slate-700 hover:bg-slate-800 transition-all duration-300"
                  >
                    <span className="font-mono text-lg text-slate-600 w-8">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 flex-wrap">
                        <span className="font-medium text-slate-200">{item.name}</span>
                        <span className="font-mono text-xs text-slate-600">{item.symbol}</span>
                        <span className="text-[10px] tracking-wide px-2 py-0.5 rounded-md bg-slate-800 text-slate-400 border border-slate-700">
                          {item.industry || '未分类'}
                        </span>
                      </div>
                      <div className="mt-3">
                        <ScoreBar label="综合" value={item.total_score} />
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="font-display text-2xl text-cyan-300">{item.total_score.toFixed(3)}</span>
                    </div>
                  </div>
                </a>
              ))}
            </div>
          </DissolveCard>
        </motion.div>

        <div className="space-y-5">
          <motion.div variants={itemVariants}>
            <DissolveCard className="glass-card rounded-2xl p-6">
              <p className="editorial-label mb-5">Score Breakdown</p>
              {topStocks[0] && (
                <div className="space-y-4">
                  <div className="pb-4 border-b border-slate-800">
                    <p className="text-xs text-slate-500">榜首</p>
                    <p className="font-display text-2xl text-slate-50">{topStocks[0].name}</p>
                  </div>
                  <ScoreBar label="质量" value={topStocks[0].quality_score} />
                  <ScoreBar label="估值" value={topStocks[0].value_score} />
                  <ScoreBar label="动量" value={topStocks[0].momentum_score} />
                </div>
              )}
            </DissolveCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <DissolveCard className="glass-card rounded-2xl p-6">
              <p className="editorial-label mb-5">Industry Distribution</p>
              {industryDistribution.length > 0 ? (
                <div className="h-52">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={industryDistribution} layout="vertical" margin={{ left: 40, right: 20, top: 5, bottom: 5 }}>
                      <XAxis type="number" hide />
                      <YAxis
                        dataKey="name"
                        type="category"
                        tick={{ fill: '#94a3b8', fontSize: 11 }}
                        width={60}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        cursor={{ fill: 'rgba(201, 168, 124, 0.05)' }}
                        contentStyle={{
                          background: '#0f172a',
                          border: '1px solid #334155',
                          borderRadius: '10px',
                          fontSize: '12px',
                          color: '#f0f4f8',
                        }}
                      />
                      <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={14}>
                        {industryDistribution.map((_, index) => (
                          <Cell key={`cell-${index}`} fill={index === 0 ? '#38bdf8' : '#475569'} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-slate-500">暂无数据</p>
              )}
            </DissolveCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <DissolveCard className="glass-card rounded-2xl p-6">
              <p className="editorial-label mb-5">Data Quality</p>
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
              <div className="mt-4 pt-4 border-t border-slate-800 flex items-center gap-2 text-xs text-slate-500">
                {qualityDetail?.total ? (
                  <>
                    <Database size={12} />
                    共 {qualityDetail.total} 条财务记录
                  </>
                ) : (
                  <span>暂无数据</span>
                )}
              </div>
              {qualityDetail?.estimation_note && (
                <div className="mt-3 text-[11px] leading-relaxed text-slate-500 glass-float rounded-lg p-3">
                  {qualityDetail.estimation_note}
                </div>
              )}
            </DissolveCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <DissolveCard className="glass-card rounded-2xl p-6">
              <p className="editorial-label mb-5">Recent Updates</p>
              <div className="space-y-3">
                {(qualityDetail?.recent_logs || []).slice(0, 5).map((log: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-2 text-xs">
                    {log.status === 'success' ? (
                      <CheckCircle2 size={12} className="text-cyan-300 mt-0.5 shrink-0" />
                    ) : (
                      <AlertCircle size={12} className="text-cyan-300 mt-0.5 shrink-0" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-slate-200 truncate">{log.message}</p>
                      <p className="text-slate-600 mt-0.5">
                        {new Date(log.time).toLocaleString('zh-CN')} · {log.provider || 'unknown'} · {log.stocks_count ?? '—'} 只
                      </p>
                    </div>
                  </div>
                ))}
                {(qualityDetail?.recent_logs || []).length === 0 && (
                  <p className="text-sm text-slate-500">暂无更新记录</p>
                )}
              </div>
            </DissolveCard>
          </motion.div>

          <motion.div variants={itemVariants}>
            <DissolveCard className="glass-card rounded-2xl p-6">
              <p className="editorial-label mb-5">System Status</p>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">数据源</span>
                  <span className="text-slate-200 flex items-center gap-1.5 glass-float px-2.5 py-1 rounded-lg">
                    <Database size={12} className="text-slate-600" />
                    {providerLabel}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">定时任务</span>
                  <span className="text-slate-200">每日 19:00</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">覆盖股票</span>
                  <span className="text-slate-200">{latestLog?.stocks_count ? `${latestLog.stocks_count} 只` : '—'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">过滤策略</span>
                  <span className="text-slate-200">行业差异化</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">数据可信度</span>
                  <span className={`text-xs ${completenessPct && completenessPct >= 70 ? 'text-cyan-300' : completenessPct && completenessPct >= 40 ? 'text-cyan-300' : 'text-fuchsia-300'}`}>
                    {completenessPct !== null ? `${completenessPct}% 完整度` : '未知'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">最近更新</span>
                  <span className="text-xs text-slate-400">
                    {latestLog ? new Date(latestLog.time).toLocaleString('zh-CN') : '—'}
                  </span>
                </div>
              </div>
            </DissolveCard>
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
