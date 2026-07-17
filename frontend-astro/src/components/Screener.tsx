import { motion } from 'framer-motion'
import { useEffect, useMemo, useState, useRef } from 'react'
import { fetchLatestSnapshot } from '../services/api'
import { Search, SlidersHorizontal, ArrowUpDown, X, RotateCcw, ArrowUp, ArrowDown } from 'lucide-react'
import DissolveCard from '../components/DissolveCard'
import { SignalBadges, formatSignalName } from '../components/SignalBadges'

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

function saveFilters(filters: { minScore: string; industry: string; sortBy: string; sortDir: string; search: string }) {
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
  const [sortDir, setSortDir] = useState<'desc' | 'asc'>(saved?.sortDir || 'desc')
  const [search, setSearch] = useState(saved?.search || '')
  const [loading, setLoading] = useState(true)
  const searchRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadItems()
  }, [])

  useEffect(() => {
    saveFilters({ minScore, industry, sortBy, sortDir, search })
  }, [minScore, industry, sortBy, sortDir, search])

  // 快捷键: / 聚焦搜索, Esc 清除
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'SELECT') {
        e.preventDefault()
        searchRef.current?.focus()
      }
      if (e.key === 'Escape' && document.activeElement === searchRef.current) {
        setSearch('')
        searchRef.current?.blur()
      }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [])

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
      return sortDir === 'desc' ? bVal - aVal : aVal - bVal
    })
  }, [filteredItems, sortBy, sortDir])

  function toggleSort(field: string) {
    if (sortBy === field) {
      setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    } else {
      setSortBy(field)
      setSortDir('desc')
    }
  }

  function SortIcon({ field }: { field: string }) {
    if (sortBy !== field) return <ArrowUpDown size={10} className="text-slate-700" />
    return sortDir === 'desc' ? <ArrowDown size={10} className="text-cyan-300" /> : <ArrowUp size={10} className="text-cyan-300" />
  }

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
                ref={searchRef}
                type="text"
                placeholder="搜索代码或名称... (按 / 聚焦)"
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
                <option value="volatility_score">低波动</option>
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
            <div className="overflow-x-auto max-h-[70vh]">
              <table className="elegant-table">
                <thead className="sticky top-0 z-10">
                  <tr className="bg-slate-900">
                    <th className="px-4 py-4 font-sans bg-slate-900">排名</th>
                    <th className="px-4 py-4 font-sans bg-slate-900">股票</th>
                    <th className="px-4 py-4 font-sans bg-slate-900">行业</th>
                    <th className="px-4 py-4 font-sans bg-slate-900">信号</th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('total_score')}>
                      <span className="inline-flex items-center gap-1 justify-end">综合 <SortIcon field="total_score" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('quality_score')}>
                      <span className="inline-flex items-center gap-1 justify-end">质量 <SortIcon field="quality_score" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('value_score')}>
                      <span className="inline-flex items-center gap-1 justify-end">估值 <SortIcon field="value_score" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('stability_score')}>
                      <span className="inline-flex items-center gap-1 justify-end">稳定 <SortIcon field="stability_score" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('volatility_score')}>
                      <span className="inline-flex items-center gap-1 justify-end">低波动 <SortIcon field="volatility_score" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('momentum_score')}>
                      <span className="inline-flex items-center gap-1 justify-end">动量 <SortIcon field="momentum_score" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('pe_ttm')}>
                      <span className="inline-flex items-center gap-1 justify-end">PE <SortIcon field="pe_ttm" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('pb')}>
                      <span className="inline-flex items-center gap-1 justify-end">PB <SortIcon field="pb" /></span>
                    </th>
                    <th className="px-4 py-4 text-right font-sans bg-slate-900 cursor-pointer select-none hover:text-slate-300 transition-colors" onClick={() => toggleSort('roe')}>
                      <span className="inline-flex items-center gap-1 justify-end">ROE <SortIcon field="roe" /></span>
                    </th>
                    <th className="px-4 py-4 font-sans bg-slate-900">入选理由</th>
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
                        {item.volatility_score?.toFixed(2) || '-'}
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
