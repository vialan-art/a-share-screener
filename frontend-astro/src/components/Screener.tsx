import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { fetchLatestSnapshot } from '../services/api'
import { Search, SlidersHorizontal, ArrowUpDown, X, RotateCcw } from 'lucide-react'
import DissolveCard from '../components/DissolveCard'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
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

function getScoreColor(score: number) {
  if (score >= 0.7) return 'text-cyan-300'
  if (score >= 0.5) return 'text-slate-200'
  return 'text-slate-500'
}

function ReasonPill({ reasons }: { reasons?: string[] }) {
  if (!reasons || reasons.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1">
      {reasons.map((r, idx) => (
        <span
          key={idx}
          className="text-[10px] px-2 py-1 rounded-md bg-slate-800 text-slate-400 whitespace-nowrap border border-slate-700"
          title={r}
        >
          {r.length > 10 ? `${r.slice(0, 10)}...` : r}
        </span>
      ))}
    </div>
  )
}

function SignalBadges({ signals }: { signals?: Record<string, any> }) {
  if (!signals) return <span className="text-slate-700 text-xs">—</span>
  const passed = Object.values(signals).filter((s: any) => s.passed === true)
  if (passed.length === 0) return <span className="text-slate-700 text-xs">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {passed.slice(0, 3).map((s: any) => (
        <span
          key={s.name}
          title={s.reason || s.name}
          className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-400/10 text-cyan-300 border border-cyan-400/20 whitespace-nowrap"
        >
          {formatSignalName(s.name)}
        </span>
      ))}
      {passed.length > 3 && (
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
          +{passed.length - 3}
        </span>
      )}
    </div>
  )
}

function formatSignalName(name: string): string {
  const map: Record<string, string> = {
    macd_golden_cross: 'MACD金叉',
    kdj: 'KDJ',
    rsi_14: 'RSI',
    bollinger: '布林',
    ma_bullish_alignment: '均线多头',
    atr_14: 'ATR',
    hammer: '锤子线',
    engulfing: '吞没',
    doji: '十字星',
    morning_star: '启明星',
    volume_breakout: '放量突破',
    platform_breakout: '平台突破',
    turtle_breakout_20: '海龟20日',
    low_atr_growth: '低波动',
    pullback_yearly_ma: '年线回踩',
    rps_breakout_120: 'RPS120',
    limit_up_shakeout: '涨停洗盘',
    uptrend_limit_down: '趋势跌停',
    high_tight_flag: '高位旗形',
    ma_volume_golden_cross: '量价金叉',
    turtle_trade_enhanced: '海龟增强',
    stock_scanner_fundamental: '基本面',
    stock_scanner_sentiment: '情绪面',
  }
  return map[name] || name
}

function parseSignals(dataJson: string | null): Record<string, any> | null {
  if (!dataJson) return null
  try {
    const d = JSON.parse(dataJson)
    return d._plugin_signals || null
  } catch {
    return null
  }
}

const STORAGE_KEY = 'screener-filters'

function loadFilters() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return null
}

function saveFilters(filters: { minScore: string; industry: string; sortBy: string; search: string }) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(filters))
  } catch {}
}

export default function Screener() {
  const saved = typeof window !== 'undefined' ? loadFilters() : null

  const [items, setItems] = useState<any[]>([])
  const [date, setDate] = useState('')
  const [minScore, setMinScore] = useState(saved?.minScore || '')
  const [industry, setIndustry] = useState(saved?.industry || '')
  const [sortBy, setSortBy] = useState(saved?.sortBy || 'total_score')
  const [search, setSearch] = useState(saved?.search || '')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadItems()
  }, [])

  useEffect(() => {
    saveFilters({ minScore, industry, sortBy, search })
  }, [minScore, industry, sortBy, search])

  async function loadItems() {
    setLoading(true)
    const data = await fetchLatestSnapshot(
      minScore ? Number(minScore) : undefined,
      industry || undefined,
    )
    setItems(data.items || [])
    setDate(data.date || '')
    setLoading(false)
  }

  function resetFilters() {
    setMinScore('')
    setIndustry('')
    setSortBy('total_score')
    setSearch('')
  }

  const hasActiveFilters = minScore !== '' || industry !== '' || search !== ''

  const filteredItems = useMemo(() => {
    let result = items
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      result = result.filter(
        (item) =>
          item.symbol?.toLowerCase().includes(q) ||
          item.name?.toLowerCase().includes(q)
      )
    }
    return result
  }, [items, search])

  const sortedItems = useMemo(() => {
    return [...filteredItems].sort((a, b) => {
      const aVal = a[sortBy] ?? -Infinity
      const bVal = b[sortBy] ?? -Infinity
      return bVal - aVal
    })
  }, [filteredItems, sortBy])

  const industries = useMemo(
    () => Array.from(new Set(items.map((i) => i.industry).filter(Boolean))).sort(),
    [items]
  )

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-6 pb-12"
    >
      <motion.div variants={itemVariants} className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <SectionHeader number="01" label="Screener" title="候选股票池" />
        <p className="text-sm text-slate-500">
          快照日期：<span className="font-mono">{date || '—'}</span> · 共 <span className="font-mono">{sortedItems.length}</span> 只
          {search && items.length !== sortedItems.length && (
            <span className="text-slate-600">（筛选自 {items.length} 只）</span>
          )}
        </p>
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="glass-card p-4 space-y-3">
          <div className="flex flex-wrap items-center gap-3">
            <div className="relative flex-1 min-w-[200px] max-w-xs">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
              <input
                type="text"
                placeholder="搜索代码或名称..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="glass-select w-full"
              />
            </div>

            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="glass-select min-w-[140px]"
            >
              <option value="">所有行业</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>

            <div className="relative">
              <SlidersHorizontal size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                placeholder="最低得分"
                value={minScore}
                onChange={(e) => setMinScore(e.target.value)}
                className="glass-select w-32"
              />
            </div>

            <div className="relative">
              <ArrowUpDown size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="glass-select min-w-[130px]"
              >
                <option value="total_score">综合得分</option>
                <option value="quality_score">质量分</option>
                <option value="value_score">估值分</option>
                <option value="stability_score">稳定分</option>
                <option value="momentum_score">动量分</option>
                <option value="pe_ttm">PE 升序</option>
                <option value="pb">PB 升序</option>
              </select>
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={loadItems}
              className="btn-primary"
            >
              应用筛选
            </motion.button>

            {hasActiveFilters && (
              <motion.button
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={resetFilters}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs text-slate-400 hover:text-slate-200 border border-slate-700 hover:border-slate-500 transition-colors"
              >
                <RotateCcw size={12} />
                重置
              </motion.button>
            )}
          </div>

          {hasActiveFilters && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              className="flex flex-wrap items-center gap-2 pt-1"
            >
              <span className="text-[10px] text-slate-600 uppercase tracking-wider">Active:</span>
              {search && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-cyan-400/10 text-cyan-300 border border-cyan-400/20">
                  搜索: {search}
                  <button onClick={() => setSearch('')} className="hover:text-cyan-100"><X size={10} /></button>
                </span>
              )}
              {industry && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-cyan-400/10 text-cyan-300 border border-cyan-400/20">
                  行业: {industry}
                  <button onClick={() => setIndustry('')} className="hover:text-cyan-100"><X size={10} /></button>
                </span>
              )}
              {minScore && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md bg-cyan-400/10 text-cyan-300 border border-cyan-400/20">
                  最低分: {minScore}
                  <button onClick={() => setMinScore('')} className="hover:text-cyan-100"><X size={10} /></button>
                </span>
              )}
            </motion.div>
          )}
        </DissolveCard>
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="glass-card overflow-hidden">
          {loading ? (
            <div className="p-12 text-center">
              <div className="w-8 h-8 border-2 border-slate-600 border-t-cyan-400 rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-slate-500">加载中...</p>
            </div>
          ) : sortedItems.length === 0 ? (
            <div className="p-12 text-center text-slate-500">
              <p className="text-sm">没有符合条件的股票</p>
              {hasActiveFilters && (
                <button onClick={resetFilters} className="mt-2 text-xs text-cyan-300 hover:text-cyan-200 underline">
                  清除筛选条件
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="elegant-table">
                <thead>
                  <tr className="bg-slate-900">
                    <th className="px-4 py-4 font-sans">排名</th>
                    <th className="px-4 py-4 font-sans">股票</th>
                    <th className="px-4 py-4 font-sans">行业</th>
                    <th className="px-4 py-4 font-sans">信号</th>
                    <th className="px-4 py-4 text-right font-sans">综合</th>
                    <th className="px-4 py-4 text-right font-sans">质量</th>
                    <th className="px-4 py-4 text-right font-sans">估值</th>
                    <th className="px-4 py-4 text-right font-sans">稳定</th>
                    <th className="px-4 py-4 text-right font-sans">动量</th>
                    <th className="px-4 py-4 text-right font-sans">PE</th>
                    <th className="px-4 py-4 text-right font-sans">PB</th>
                    <th className="px-4 py-4 text-right font-sans">ROE</th>
                    <th className="px-4 py-4 font-sans">入选理由</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedItems.map((item, index) => (
                    <tr key={item.symbol} className="group">
                      <td className="px-4 py-4">
                        <span className="font-mono text-sm text-slate-600">
                          {String(index + 1).padStart(2, '0')}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <a
                          href={`/stock/?symbol=${item.symbol}`}
                          className="block hover:text-slate-50 transition-colors"
                        >
                          <span className="font-medium text-slate-200">{item.name}</span>
                          <span className="block font-mono text-[10px] text-slate-600 mt-0.5">{item.symbol}</span>
                        </a>
                      </td>
                      <td className="px-4 py-4">
                        <span className="text-[10px] px-2 py-1 rounded-md bg-slate-800 text-slate-400 border border-slate-700 whitespace-nowrap">
                          {item.industry || '未分类'}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <SignalBadges signals={item._signals} />
                      </td>
                      <td className={`px-4 py-4 text-right font-display text-lg ${getScoreColor(item.total_score)}`}>
                        {item.total_score.toFixed(3)}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.quality_score.toFixed(2)}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.value_score.toFixed(2)}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.stability_score?.toFixed(2) || '-'}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.momentum_score.toFixed(2)}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.pe_ttm?.toFixed(2) || '-'}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.pb?.toFixed(2) || '-'}
                      </td>
                      <td className="px-4 py-4 text-right font-mono text-sm text-slate-400">
                        {item.roe?.toFixed(2) || '-'}%
                      </td>
                      <td className="px-4 py-4">
                        <ReasonPill reasons={item._reasons} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DissolveCard>
      </motion.div>
    </motion.div>
  )
}
