import { motion } from 'framer-motion'
import { useEffect, useState, useMemo } from 'react'
import { fetchStockDetail } from '../services/api'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts'
import { ArrowLeft, AlertTriangle, CheckCircle2, Database, Clock, ShieldAlert } from 'lucide-react'

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

function MetricCard({ label, value, unit = '' }: { label: string; value: any; unit?: string }) {
  const displayValue = value !== null && value !== undefined
    ? (typeof value === 'number' ? value.toFixed(2) : value)
    : '—'

  return (
    <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-700/40 hover:border-cyan-400/30 transition-colors">
      <p className="text-[10px] tracking-[0.15em] text-slate-500 uppercase mb-1">{label}</p>
      <p className="font-mono text-lg text-slate-50">
        {displayValue}
        {unit && value !== null && value !== undefined && (
          <span className="text-sm text-slate-500 ml-0.5">{unit}</span>
        )}
      </p>
    </div>
  )
}

function QualityBanner({ quality }: { quality: any }) {
  if (!quality) return null
  const completeness = quality.completeness_score ?? 0
  const issues = quality.issues || []
  const isReliable = completeness >= 0.7 && issues.length === 0

  return (
    <div className={`rounded-xl p-4 border ${isReliable ? 'bg-cyan-400/5 border-cyan-400/20' : 'bg-fuchsia-400/5 border-fuchsia-400/20'}`}>
      <div className="flex items-start gap-3">
        {isReliable ? (
          <Database size={16} className="text-cyan-300 mt-0.5 shrink-0" />
        ) : (
          <ShieldAlert size={16} className="text-fuchsia-300 mt-0.5 shrink-0" />
        )}
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <p className={`text-xs font-medium ${isReliable ? 'text-cyan-300' : 'text-fuchsia-300'}`}>
              数据质量
            </p>
            <span className="text-[10px] text-slate-500">
              完整度 {(completeness * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-600 mb-2">
            <Clock size={12} />
            <span>来源: {quality.source || 'unknown'}</span>
            <span>·</span>
            <span>更新: {quality.freshness ? new Date(quality.freshness).toLocaleString('zh-CN') : '未知'}</span>
          </div>
          {issues.length > 0 && (
            <ul className="space-y-1">
              {issues.map((issue: string, idx: number) => (
                  <li key={idx} className="text-xs text-fuchsia-300 flex items-start gap-1.5">
                    <span className="w-1 h-1 rounded-full bg-fuchsia-400 mt-1.5 shrink-0" />
                  {issue}
                </li>
              ))}
            </ul>
          )}
          {quality.data_source_note && (
            <div className="mt-3 rounded-lg border border-slate-700/40 bg-slate-900/40 p-3">
              <p className="text-[10px] tracking-widest text-slate-500 uppercase mb-1">数据来源说明</p>
              <p className="text-xs text-slate-600 leading-relaxed">{quality.data_source_note}</p>
            </div>
          )}
          <p className="text-[10px] text-slate-400 mt-2">
            数据来自第三方接口，可能存在延迟或错误，仅供学习研究，不构成投资建议。
          </p>
        </div>
      </div>
    </div>
  )
}

export default function StockDetail() {
  const [data, setData] = useState<any>(null)
  const [symbol, setSymbol] = useState<string>('')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const s = params.get('symbol') || ''
    setSymbol(s)
    if (s) {
      fetchStockDetail(s).then(setData)
    }
  }, [])

  const metrics = data?.metrics || {}
  const score = data?.score || {}
  const dataQuality = data?.data_quality || {}

  const radarData = useMemo(() => {
    if (!data) return []
    return [
      { subject: '质量', A: (score.quality || 0) * 100, fullMark: 100 },
      { subject: '估值', A: (score.value || 0) * 100, fullMark: 100 },
      { subject: '动量', A: (score.momentum || 0) * 100, fullMark: 100 },
      { subject: 'ROE', A: Math.min((metrics.roe || 0) * 3, 100), fullMark: 100 },
      { subject: '成长', A: Math.min(Math.max((metrics.profit_deducted_growth || metrics.profit_growth || 0) + 50, 0), 100), fullMark: 100 },
    ]
  }, [data, score, metrics])

  if (!data) {
    return (
      <div className="h-96 flex items-center justify-center text-slate-500">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-slate-500 border-t-cyan-400 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-sm tracking-wide">正在加载...</p>
        </div>
      </div>
    )
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8"
    >
      <motion.div variants={itemVariants}>
        <a
          href="/screener/"
          className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-50 transition-colors mb-6"
        >
          <ArrowLeft size={14} strokeWidth={1.5} />
          返回选股池
        </a>
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="glass-card rounded-2xl p-8 relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-cyan-400/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="relative">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[10px] tracking-[0.25em] text-slate-500 uppercase">{data.market} · {data.symbol}</p>
              <h2 className="font-serif text-5xl text-slate-50 mt-2">{data.name}</h2>
              <div className="flex items-center gap-3 mt-4">
                <span className="text-xs px-3 py-1.5 rounded-full bg-slate-800 text-slate-600">
                  {data.industry || '未分类'}
                </span>
                {score.passed_filters ? (
                  <span className="inline-flex items-center gap-1 text-xs text-cyan-300">
                    <CheckCircle2 size={12} /> 通过过滤
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-fuchsia-300">
                    <AlertTriangle size={12} /> 未通过过滤
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <p className="text-[10px] tracking-[0.2em] text-slate-500 uppercase">综合得分</p>
              <p className={`font-serif text-6xl ${score.total >= 0.7 ? 'text-cyan-300' : 'text-slate-50'}`}>
                {score.total?.toFixed(3) || '—'}
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
          <p className="text-[10px] tracking-[0.2em] text-slate-500 uppercase mb-6">Score Radar</p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#94a3b8" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fill: '#94a3b8', fontSize: 12 }}
                />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar
                  name={data.name}
                  dataKey="A"
                  stroke="#7dd3fc"
                  strokeWidth={2}
                  fill="#7dd3fc"
                  fillOpacity={0.2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

      <motion.div variants={itemVariants} className="lg:col-span-2 glass-card rounded-2xl p-6">
        <p className="text-[10px] tracking-[0.2em] text-slate-500 uppercase mb-6">Key Metrics</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="ROE" value={metrics.roe} unit="%" />
          <MetricCard label="ROA" value={metrics.roa} unit="%" />
          <MetricCard label="毛利率" value={metrics.gross_margin} unit="%" />
          <MetricCard label="净利率" value={metrics.net_margin} unit="%" />
          <MetricCard label="营收增长" value={metrics.revenue_growth} unit="%" />
          <MetricCard label="净利润增长" value={metrics.profit_growth} unit="%" />
          <MetricCard label="扣非净利润增长" value={metrics.profit_deducted_growth} unit="%" />
          <MetricCard label="资产负债率" value={metrics.debt_to_asset} unit="%" />
          <MetricCard label="有息负债率" value={metrics.interest_bearing_debt_ratio} unit="%" />
          <MetricCard label="流动比率" value={metrics.current_ratio} />
          <MetricCard label="速动比率" value={metrics.quick_ratio} />
          <MetricCard label="经营现金流" value={metrics.operating_cash_flow} unit="亿" />
          <MetricCard label="自由现金流" value={metrics.free_cash_flow} unit="亿" />
          <MetricCard label="经营现金流/净利润" value={metrics.ocf_to_net_profit} />
          <MetricCard label="PE TTM" value={metrics.pe_ttm} />
          <MetricCard label="PB" value={metrics.pb} />
          <MetricCard label="股息率" value={metrics.dividend_yield} unit="%" />
          <MetricCard label="审计意见" value={metrics.audit_opinion} />
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="lg:col-span-3">
        <QualityBanner quality={dataQuality} />
      </motion.div>
      </div>

      {!score.passed_filters && score.filter_reasons && score.filter_reasons !== '[]' && (
        <motion.div
          variants={itemVariants}
          className="glass-card rounded-2xl p-6 border-fuchsia-400/20 bg-fuchsia-400/5"
        >
          <p className="text-[10px] tracking-[0.2em] text-fuchsia-300 uppercase mb-3">Filter Failures</p>
          <ul className="space-y-2">
            {JSON.parse(score.filter_reasons).map((reason: string, idx: number) => (
              <li key={idx} className="text-sm text-fuchsia-300 flex items-start gap-2">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                {reason}
              </li>
            ))}
          </ul>
        </motion.div>
      )}
    </motion.div>
  )
}
