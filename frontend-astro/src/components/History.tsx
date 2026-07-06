import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { fetchSnapshotDates, fetchSnapshotByDate } from '../services/api'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
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
    }
  }, [selectedDate])

  const currentIndex = dates.indexOf(selectedDate)

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 pb-12"
    >
      <motion.div variants={itemVariants} className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
        <SectionHeader number="02" label="History" title="历史存档" />

        <div className="flex items-center gap-3">
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
                  <th className="px-6 py-4 text-right">综合得分</th>
                  <th className="px-6 py-4 text-right">PE</th>
                  <th className="px-6 py-4 text-right">PB</th>
                  <th className="px-6 py-4 text-right">ROE</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, index) => (
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
                    <td className="px-6 py-4 text-right font-display text-xl text-cyan-300">
                      {item.total_score.toFixed(3)}
                    </td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">{item.pe_ttm?.toFixed(2) || '-'}</td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">{item.pb?.toFixed(2) || '-'}</td>
                    <td className="px-6 py-4 text-right font-mono text-sm text-slate-600">{item.roe?.toFixed(2) || '-'}%</td>
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
