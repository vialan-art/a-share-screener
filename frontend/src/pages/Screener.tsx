import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchLatestSnapshot } from '../services/api'
import { Search, SlidersHorizontal, ArrowUpDown } from 'lucide-react'

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 12 },
  visible: { opacity: 1, y: 0 },
}

function getScoreColor(score: number) {
  if (score >= 0.7) return 'text-moss'
  if (score >= 0.5) return 'text-ink-700'
  return 'text-ink-500'
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
      className="space-y-6"
    >
      <motion.div variants={itemVariants} className="flex items-end justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">Screener</p>
          <h2 className="font-serif text-4xl text-sumi">候选股票池</h2>
          <p className="text-sm text-ink-500 mt-2">
            快照日期：<span className="font-mono">{date || '—'}</span> · 共 <span className="font-mono">{items.length}</span> 只
          </p>
        </div>
      </motion.div>

      {/* Filters */}
      <motion.div
        variants={itemVariants}
        className="glass-card rounded-2xl p-5 flex flex-wrap items-center gap-4"
      >
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
          <select
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="pl-9 pr-8 py-2.5 bg-ink-50 border border-ink-200/60 rounded-lg text-sm text-sumi focus:outline-none focus:border-moss/50 appearance-none min-w-[160px]"
          >
            <option value="">所有行业</option>
            {industries.map((ind) => (
              <option key={ind} value={ind}>{ind}</option>
            ))}
          </select>
        </div>

        <div className="relative">
          <SlidersHorizontal size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
          <input
            type="number"
            step="0.1"
            min="0"
            max="1"
            placeholder="最低得分"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="pl-9 pr-4 py-2.5 bg-ink-50 border border-ink-200/60 rounded-lg text-sm text-sumi focus:outline-none focus:border-moss/50 w-36"
          />
        </div>

        <div className="relative">
          <ArrowUpDown size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="pl-9 pr-8 py-2.5 bg-ink-50 border border-ink-200/60 rounded-lg text-sm text-sumi focus:outline-none focus:border-moss/50 appearance-none min-w-[140px]"
          >
            <option value="total_score">综合得分</option>
            <option value="quality_score">质量分</option>
            <option value="value_score">估值分</option>
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
      </motion.div>

      {/* Table */}
      <motion.div variants={itemVariants} className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="elegant-table">
            <thead>
              <tr className="bg-ink-100/40">
                <th className="px-6 py-4 font-sans">排名</th>
                <th className="px-6 py-4 font-sans">股票</th>
                <th className="px-6 py-4 font-sans">行业</th>
                <th className="px-6 py-4 text-right font-sans">综合</th>
                <th className="px-6 py-4 text-right font-sans">质量</th>
                <th className="px-6 py-4 text-right font-sans">估值</th>
                <th className="px-6 py-4 text-right font-sans">动量</th>
                <th className="px-6 py-4 text-right font-sans">PE</th>
                <th className="px-6 py-4 text-right font-sans">PB</th>
                <th className="px-6 py-4 text-right font-sans">ROE</th>
              </tr>
            </thead>
            <tbody>
              {sortedItems.map((item, index) => (
                <tr key={item.symbol} className="group">
                  <td className="px-6 py-4">
                    <span className="font-serif text-lg text-ink-300">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <Link
                      to={`/stock/${item.symbol}`}
                      className="block hover:text-moss transition-colors"
                    >
                      <span className="font-medium text-sumi">{item.name}</span>
                      <span className="block font-mono text-[10px] text-ink-400 mt-0.5">{item.symbol}</span>
                    </Link>
                  </td>
                  <td className="px-6 py-4">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-ink-100/70 text-ink-600 whitespace-nowrap">
                      {item.industry || '未分类'}
                    </span>
                  </td>
                  <td className={`px-6 py-4 text-right font-serif text-lg ${getScoreColor(item.total_score)}`}>
                    {item.total_score.toFixed(3)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.quality_score.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.value_score.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.momentum_score.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.pe_ttm?.toFixed(2) || '-'}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.pb?.toFixed(2) || '-'}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">
                    {item.roe?.toFixed(2) || '-'}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
