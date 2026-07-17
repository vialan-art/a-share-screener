import { motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import { fetchSnapshotDates, fetchSnapshotByDate } from '../services/api'
import { Calendar, ChevronLeft, ChevronRight, ArrowUpRight, ArrowDownRight, Minus, GitCompareArrows } from 'lucide-react'
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
      <p className="editorial-label mb-3">( {number} ) · {label}</p>
      <h2 className="font-display text-4xl lg:text-5xl text-slate-50">{title}</h2>
    </div>
  )
}

export default function History() {
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [items, setItems] = useState<any[]>([])
  const [prevItems, setPrevItems] = useState<any[]>([])
  const [compareMode, setCompareMode] = useState(false)
  const [compareDate, setCompareDate] = useState('')
  const [compareItems, setCompareItems] = useState<any[]>([])

  useEffect(() => {
    fetchSnapshotDates().then((d) => {
      setDates(d)
      if (d.length > 0 && !selectedDate) {
        setSelectedDate(d[0])
      }
    })
  }, [])

  useEffect(() => {
    if (selectedDate) {
      fetchSnapshotByDate(selectedDate).then((data) => setItems(data.items || []))
      const idx = dates.indexOf(selectedDate)
      if (idx >= 0 && idx < dates.length - 1) {
        fetchSnapshotByDate(dates[idx + 1]).then((data) => setPrevItems(data.items || []))
      } else {
        setPrevItems([])
      }
    }
  }, [selectedDate, dates])

  useEffect(() => {
    if (compareDate) {
      fetchSnapshotByDate(compareDate).then((data) => setCompareItems(data.items || []))
    } else {
      setCompareItems([])
    }
  }, [compareDate])

  const currentIndex = dates.indexOf(selectedDate)

  const prevTop10Symbols = useMemo(
    () => new Set(prevItems.slice(0, 10).map((i: any) => i.symbol)),
    [prevItems]
  )

  const compareTop10Map = useMemo(() => {
    const map: Record<string, number> = {}
    compareItems.slice(0, 10).forEach((item: any, idx: number) => {
      map[item.symbol] = idx + 1
    })
    return map
  }, [compareItems])

  function getChangeTag(item: any, index: number) {
    if (compareMode && compareItems.length > 0) {
      if (index >= 10) return null
      const compareRank = compareTop10Map[item.symbol]
      if (compareRank === undefined) return { label: '新进', color: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/20', icon: ArrowUpRight }
      const diff = compareRank - (index + 1)
      if (diff > 0) return { label: `+${diff}`, color: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/20', icon: ArrowUpRight }
      if (diff < 0) return { label: `${diff}`, color: 'text-fuchsia-300 bg-fuchsia-400/10 border-fuchsia-400/20', icon: ArrowDownRight }
      return null
    }
    if (prevItems.length === 0) return null
    const inCurrentTop10 = index < 10
    const inPrevTop10 = prevTop10Symbols.has(item.symbol)
    if (inCurrentTop10 && !inPrevTop10) return { label: '新进', color: 'text-cyan-300 bg-cyan-400/10 border-cyan-400/20', icon: ArrowUpRight }
    if (!inCurrentTop10 && inPrevTop10) return { label: '掉出', color: 'text-fuchsia-300 bg-fuchsia-400/10 border-fuchsia-400/20', icon: ArrowDownRight }
    return null
  }

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 pb-12"
    >
      <motion.div variants={itemVariants} className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <SectionHeader number="02" label="History" title="历史存档" />

        <div className="flex items-center gap-3 flex-wrap">
          <button
            onClick={() => {
              setCompareMode(!compareMode)
              if (compareMode) setCompareDate('')
            }}
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs border transition-colors ${
              compareMode
                ? 'border-cyan-400/30 text-cyan-300 bg-cyan-400/5'
                : 'border-slate-700 text-slate-500 hover:text-slate-300'
            }`}
          >
            <GitCompareArrows size={12} />
            {compareMode ? '退出对比' : '对比模式'}
          </button>

          {compareMode && (
            <select
              value={compareDate}
              onChange={(e) => setCompareDate(e.target.value)}
              className="glass-select min-w-[120px] text-sm"
            >
              <option value="">选择对比日期</option>
              {dates.filter((d) => d !== selectedDate).map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          )}

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => currentIndex < dates.length - 1 && setSelectedDate(dates[currentIndex + 1])}
            disabled={currentIndex >= dates.length - 1}
            className="p-2.5 rounded-xl border border-slate-600 text-slate-500 hover:bg-slate-800 disabled:opacity-30 glass-float"
          >
            <ChevronLeft size={16} />
          </motion.button>

          <div className="flex items-center gap-2 px-4 py-2.5 liquid-glass rounded-xl">
            <Calendar size={14} className="text-cyan-300" />
            <span className="font-mono text-sm text-slate-50">{selectedDate || '—'}</span>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => currentIndex > 0 && setSelectedDate(dates[currentIndex - 1])}
            disabled={currentIndex <= 0}
            className="p-2.5 rounded-xl border border-slate-600 text-slate-500 hover:bg-slate-800 disabled:opacity-30 glass-float"
          >
            <ChevronRight size={16} />
          </motion.button>
        </div>
      </motion.div>

      <motion.div variants={itemVariants} className="flex flex-wrap gap-2">
        {dates.map((date) => (
          <motion.button
            key={date}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => setSelectedDate(date)}
            className={`px-4 py-2 rounded-xl text-sm transition-all duration-300 ${
              selectedDate === date
                ? 'bg-slate-900 text-slate-50 shadow-soft'
                : 'glass-float text-slate-600 hover:bg-slate-800'
            }`}
          >
            {date}
          </motion.button>
        ))}
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="liquid-glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="elegant-table">
              <thead>
                <tr className="bg-slate-800/30">
                  <th className="px-6 py-4">排名</th>
                  <th className="px-6 py-4">代码</th>
                  <th className="px-6 py-4">名称</th>
                  <th className="px-6 py-4">行业</th>
                  <th className="px-6 py-4">变动</th>
                  <th className="px-6 py-4 text-right">综合得分</th>
                  <th className="px-6 py-4 text-right">PE</th>
                  <th className="px-6 py-4 text-right">PB</th>
                  <th className="px-6 py-4 text-right">ROE</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => {
                  const tag = getChangeTag(item, index)
                  const TagIcon = tag?.icon || Minus
                  return (
                    <tr key={item.symbol} className="group">
                      <td className="px-6 py-4">
                        <span className="font-display text-xl text-slate-200 italic">
                          {String(index + 1).padStart(2, '0')}
                        </span>
                      </td>
                      <td className="px-6 py-4 font-mono text-sm text-slate-600">{item.symbol}</td>
                      <td className="px-6 py-4 font-medium text-slate-50">{item.name}</td>
                      <td className="px-6 py-4">
                        <span className="text-[10px] tracking-wide px-2.5 py-1 rounded-full glass-float text-slate-600">
                          {item.industry || '未分类'}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        {tag ? (
                          <span className={`inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-md border ${tag.color}`}>
                            <TagIcon size={10} />
                            {tag.label}
                          </span>
                        ) : (
                          <span className="text-slate-700 text-xs">—</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-right font-display text-xl text-cyan-300">
                        {item.total_score.toFixed(3)}
                      </td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">{item.pe_ttm?.toFixed(2) || '-'}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">{item.pb?.toFixed(2) || '-'}</td>
                      <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">{item.roe?.toFixed(2) || '-'}%</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </DissolveCard>
      </motion.div>
    </motion.div>
  )
}
