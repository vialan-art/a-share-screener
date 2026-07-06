import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { fetchLatestSnapshot } from '../services/api'
import { Search, SlidersHorizontal, ArrowUpDown } from 'lucide-react'
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

export default function Screener() {
  const [items, setItems] = useState<any[]>([])
  const [date, setDate] = useState('')
  const [minScore, setMinScore] = useState('')
  const [industry, setIndustry] = useState('')
  const [sortBy, setSortBy] = useState('total_score')

  useEffect(() => {
    loadItems()
  }, [])

  async function loadItems() {
    const data = await fetchLatestSnapshot(
      minScore ? Number(minScore) : undefined,
      industry || undefined,
    )
    setItems(data.items || [])
    setDate(data.date || '')
  }

  const sortedItems = [...items].sort((a, b) => {
    const aVal = a[sortBy] ?? -Infinity
    const bVal = b[sortBy] ?? -Infinity
    return bVal - aVal
  })

  const industries = Array.from(new Set(items.map((i) => i.industry).filter(Boolean))).sort()

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
          快照日期：<span className="font-mono">{date || '—'}</span> · 共 <span className="font-mono">{items.length}</span> 只
        </p>
      </motion.div>

      <motion.div
        variants={itemVariants}
      >
        <DissolveCard className="glass-card p-4 flex flex-wrap items-center gap-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
            <select
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              className="glass-select min-w-[160px]"
            >
              <option value="">所有行业</option>
              {industries.map((ind) => (
                <option key={ind} value={ind}>{ind}</option>
              ))}
            </select>
          </div>

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
              className="glass-select w-36"
            />
          </div>

          <div className="relative">
            <ArrowUpDown size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="glass-select min-w-[140px]"
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
        </DissolveCard>
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="glass-card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="elegant-table">
              <thead>
                <tr className="bg-slate-900">
                  <th className="px-5 py-4 font-sans">排名</th>
                  <th className="px-5 py-4 font-sans">股票</th>
                  <th className="px-5 py-4 font-sans">行业</th>
                  <th className="px-5 py-4 text-right font-sans">综合</th>
                  <th className="px-5 py-4 text-right font-sans">质量</th>
                  <th className="px-5 py-4 text-right font-sans">估值</th>
                  <th className="px-5 py-4 text-right font-sans">稳定</th>
                  <th className="px-5 py-4 text-right font-sans">动量</th>
                  <th className="px-5 py-4 text-right font-sans">PE</th>
                  <th className="px-5 py-4 text-right font-sans">PB</th>
                  <th className="px-5 py-4 text-right font-sans">ROE</th>
                  <th className="px-5 py-4 font-sans">入选理由</th>
                </tr>
              </thead>
              <tbody>
                {sortedItems.map((item, index) => (
                  <tr key={item.symbol} className="group">
                    <td className="px-5 py-4">
                      <span className="font-mono text-sm text-slate-600">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                    </td>
                    <td className="px-5 py-4">
                      <a
                        href={`/stock/?symbol=${item.symbol}`}
                        className="block hover:text-slate-50 transition-colors"
                      >
                        <span className="font-medium text-slate-200">{item.name}</span>
                        <span className="block font-mono text-[10px] text-slate-600 mt-0.5">{item.symbol}</span>
                      </a>
                    </td>
                    <td className="px-5 py-4">
                      <span className="text-[10px] px-2 py-1 rounded-md bg-slate-800 text-slate-400 border border-slate-700 whitespace-nowrap">
                        {item.industry || '未分类'}
                      </span>
                    </td>
                    <td className={`px-5 py-4 text-right font-display text-lg ${getScoreColor(item.total_score)}`}>
                      {item.total_score.toFixed(3)}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.quality_score.toFixed(2)}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.value_score.toFixed(2)}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.stability_score?.toFixed(2) || '-'}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.momentum_score.toFixed(2)}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.pe_ttm?.toFixed(2) || '-'}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.pb?.toFixed(2) || '-'}
                    </td>
                    <td className="px-5 py-4 text-right font-mono text-sm text-slate-400">
                      {item.roe?.toFixed(2) || '-'}%
                    </td>
                    <td className="px-5 py-4">
                      <ReasonPill reasons={item._reasons} />
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
