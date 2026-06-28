import { motion } from 'framer-motion'
import { useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchStockDetail } from '../services/api'
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
} from 'recharts'
import { ArrowLeft, AlertTriangle, CheckCircle2 } from 'lucide-react'

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
    <div className="p-4 rounded-xl bg-ink-50/60 border border-ink-200/40 hover:border-moss/30 transition-colors">
      <p className="text-[10px] tracking-[0.15em] text-ink-500 uppercase mb-1">{label}</p>
      <p className="font-mono text-lg text-sumi">
        {displayValue}
        {unit && value !== null && value !== undefined && (
          <span className="text-sm text-ink-500 ml-0.5">{unit}</span>
        )}
      </p>
    </div>
  )
}

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    if (symbol) {
      fetchStockDetail(symbol).then(setData)
    }
  }, [symbol])

  const metrics = data?.metrics || {}
  const score = data?.score || {}

  const radarData = useMemo(() => {
    if (!data) return []
    return [
      { subject: '质量', A: (score.quality || 0) * 100, fullMark: 100 },
      { subject: '估值', A: (score.value || 0) * 100, fullMark: 100 },
      { subject: '动量', A: (score.momentum || 0) * 100, fullMark: 100 },
      { subject: 'ROE', A: Math.min((metrics.roe || 0) * 3, 100), fullMark: 100 },
      { subject: '成长', A: Math.min(Math.max((metrics.profit_growth || 0) + 50, 0), 100), fullMark: 100 },
    ]
  }, [data, score, metrics])

  if (!data) {
    return (
      <div className="h-96 flex items-center justify-center text-ink-500">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-ink-300 border-t-moss rounded-full animate-spin mx-auto mb-4" />
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
        <Link
          to="/screener"
          className="inline-flex items-center gap-2 text-sm text-ink-500 hover:text-sumi transition-colors mb-6"
        >
          <ArrowLeft size={14} strokeWidth={1.5} />
          返回选股池
        </Link>
      </motion.div>

      <motion.div
        variants={itemVariants}
        className="glass-card rounded-2xl p-8 relative overflow-hidden"
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-moss/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2" />
        <div className="relative">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase">{data.market} · {data.symbol}</p>
              <h2 className="font-serif text-5xl text-sumi mt-2">{data.name}</h2>
              <div className="flex items-center gap-3 mt-4">
                <span className="text-xs px-3 py-1.5 rounded-full bg-ink-100 text-ink-700">
                  {data.industry || '未分类'}
                </span>
                {score.passed_filters ? (
                  <span className="inline-flex items-center gap-1 text-xs text-moss">
                    <CheckCircle2 size={12} /> 通过过滤
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs text-rust">
                    <AlertTriangle size={12} /> 未通过过滤
                  </span>
                )}
              </div>
            </div>
            <div className="text-right">
              <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase">综合得分</p>
              <p className={`font-serif text-6xl ${score.total >= 0.7 ? 'text-moss' : 'text-sumi'}`}>
                {score.total?.toFixed(3) || '—'}
              </p>
            </div>
          </div>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div variants={itemVariants} className="glass-card rounded-2xl p-6">
          <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-6">Score Radar</p>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                <PolarGrid stroke="#dddad4" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fill: '#6e665c', fontSize: 12 }}
                />
                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                <Radar
                  name={data.name}
                  dataKey="A"
                  stroke="#6b7b5f"
                  strokeWidth={2}
                  fill="#6b7b5f"
                  fillOpacity={0.2}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        <motion.div variants={itemVariants} className="lg:col-span-2 glass-card rounded-2xl p-6">
          <p className="text-[10px] tracking-[0.2em] text-ink-500 uppercase mb-6">Key Metrics</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="ROE" value={metrics.roe} unit="%" />
            <MetricCard label="ROA" value={metrics.roa} unit="%" />
            <MetricCard label="毛利率" value={metrics.gross_margin} unit="%" />
            <MetricCard label="净利率" value={metrics.net_margin} unit="%" />
            <MetricCard label="营收增长" value={metrics.revenue_growth} unit="%" />
            <MetricCard label="净利润增长" value={metrics.profit_growth} unit="%" />
            <MetricCard label="资产负债率" value={metrics.debt_to_asset} unit="%" />
            <MetricCard label="流动比率" value={metrics.current_ratio} />
            <MetricCard label="PE TTM" value={metrics.pe_ttm} />
            <MetricCard label="PB" value={metrics.pb} />
            <MetricCard label="股息率" value={metrics.dividend_yield} unit="%" />
            <MetricCard label="审计意见" value={metrics.audit_opinion} />
          </div>
        </motion.div>
      </div>

      {!score.passed_filters && score.filter_reasons && score.filter_reasons !== '[]' && (
        <motion.div
          variants={itemVariants}
          className="glass-card rounded-2xl p-6 border-rust/20 bg-rust/5"
        >
          <p className="text-[10px] tracking-[0.2em] text-rust uppercase mb-3">Filter Failures</p>
          <ul className="space-y-2">
            {JSON.parse(score.filter_reasons).map((reason: string, idx: number) => (
              <li key={idx} className="text-sm text-rust flex items-start gap-2">
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
