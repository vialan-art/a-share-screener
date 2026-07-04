import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { fetchSnapshotDates, fetchSnapshotByDate } from '../services/api'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'

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
      className="space-y-6"
    >
      <motion.div variants={itemVariants} className="flex items-end justify-between">
        <div>
          <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">History</p>
          <h2 className="font-serif text-4xl text-sumi">历史存档</h2>
        </div>

        <div className="flex items-center gap-3">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => currentIndex < dates.length - 1 && setSelectedDate(dates[currentIndex + 1])}
            disabled={currentIndex >= dates.length - 1}
            className="p-2 rounded-lg border border-ink-200/60 text-ink-500 hover:bg-ink-100 disabled:opacity-30"
          >
            <ChevronLeft size={16} />
          </motion.button>

          <div className="flex items-center gap-2 px-4 py-2 glass-card rounded-lg">
            <Calendar size={14} className="text-ink-400" />
            <span className="font-mono text-sm text-sumi">{selectedDate || '—'}</span>
          </div>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => currentIndex > 0 && setSelectedDate(dates[currentIndex - 1])}
            disabled={currentIndex <= 0}
            className="p-2 rounded-lg border border-ink-200/60 text-ink-500 hover:bg-ink-100 disabled:opacity-30"
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
            className={`px-4 py-2 rounded-lg text-sm transition-all duration-300 ${
              selectedDate === date
                ? 'bg-sumi text-ink-50 shadow-soft'
                : 'glass-card text-ink-600 hover:bg-ink-100/60'
            }`}
          >
            {date}
          </motion.button>
        ))}
      </motion.div>

      <motion.div variants={itemVariants} className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="elegant-table">
            <thead>
              <tr className="bg-ink-100/40">
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
                    <span className="font-serif text-lg text-ink-300">
                      {String(index + 1).padStart(2, '0')}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono text-sm text-ink-600">{item.symbol}</td>
                  <td className="px-6 py-4 font-medium text-sumi">{item.name}</td>
                  <td className="px-6 py-4">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-ink-100/70 text-ink-600">
                      {item.industry || '未分类'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right font-serif text-lg text-moss">
                    {item.total_score.toFixed(3)}
                  </td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">{item.pe_ttm?.toFixed(2) || '-'}</td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">{item.pb?.toFixed(2) || '-'}</td>
                  <td className="px-6 py-4 text-right font-mono text-sm text-ink-600">{item.roe?.toFixed(2) || '-'}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </motion.div>
    </motion.div>
  )
}
