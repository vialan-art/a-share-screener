import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { fetchLogs } from '../services/api'
import { Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'

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

function StatusIcon({ status }: { status: string }) {
  if (status === 'success') return <CheckCircle2 size={16} className="text-moss" />
  if (status === 'failed') return <XCircle size={16} className="text-rust" />
  return <AlertCircle size={16} className="text-amber-600" />
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
      className="space-y-6"
    >
      <motion.div variants={itemVariants}>
        <p className="text-[10px] tracking-[0.25em] text-ink-500 uppercase mb-2">Logs</p>
        <h2 className="font-serif text-4xl text-sumi">运行日志</h2>
      </motion.div>

      <motion.div variants={itemVariants} className="glass-card rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="elegant-table">
            <thead>
              <tr className="bg-ink-100/40">
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
                        log.status === 'success' ? 'text-moss' :
                        log.status === 'failed' ? 'text-rust' : 'text-amber-600'
                      }`}>
                        {log.status}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2 text-sm text-ink-600">
                      <Clock size={14} className="text-ink-400" />
                      {new Date(log.time).toLocaleString('zh-CN')}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="font-mono text-sm text-ink-600">{log.stocks_count || '—'}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-ink-700 max-w-xl truncate">
                    {log.message}
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
