import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { fetchLogs } from '../services/api'
import { Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
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

function StatusIcon({ status }: { status: string }) {
  if (status === 'success') return <CheckCircle2 size={16} className="text-cyan-300" />
  if (status === 'failed') return <XCircle size={16} className="text-fuchsia-300" />
  return <AlertCircle size={16} className="text-cyan-300" />
}

export default function Logs() {
  const [logs, setLogs] = useState<any[]>([])

  useEffect(() => {
    fetchLogs().then(setLogs)
  }, [])

  return (
    <motion.div
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      className="space-y-8 pb-12"
    >
      <motion.div variants={itemVariants}>
        <SectionHeader number="02" label="Logs" title="运行日志" />
      </motion.div>

      <motion.div variants={itemVariants}>
        <DissolveCard className="liquid-glass overflow-hidden">
          <div className="overflow-x-auto">
            <table className="elegant-table">
              <thead>
                <tr className="bg-slate-800/30">
                  <th className="px-6 py-4">状态</th>
                  <th className="px-6 py-4">时间</th>
                  <th className="px-6 py-4">股票数</th>
                  <th className="px-6 py-4">消息</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, index) => (
                  <tr key={index} className="group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <StatusIcon status={log.status} />
                        <span className={`text-sm capitalize ${
                          log.status === 'success' ? 'text-cyan-300' :
                          log.status === 'failed' ? 'text-fuchsia-300' : 'text-cyan-300'
                        }`}>
                          {log.status}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-sm text-slate-600">
                        <Clock size={14} className="text-slate-400" />
                        {new Date(log.time).toLocaleString('zh-CN')}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="font-mono text-sm text-slate-600">{log.stocks_count || '—'}</span>
                    </td>
                    <td className="px-6 py-4 text-sm text-slate-600 max-w-xl truncate">
                      {log.message}
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
