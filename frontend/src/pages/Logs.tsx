import { useEffect, useState } from 'react'
import { fetchLogs } from '../services/api'

export default function Logs() {
  const [logs, setLogs] = useState<any[]>([])

  useEffect(() => {
    fetchLogs().then(setLogs)
  }, [])

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">运行日志</h2>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">时间</th>
              <th className="px-4 py-3 text-left">状态</th>
              <th className="px-4 py-3 text-left">股票数</th>
              <th className="px-4 py-3 text-left">消息</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log, index) => (
              <tr key={index} className="border-t">
                <td className="px-4 py-3 font-mono text-xs">{log.time}</td>
                <td className="px-4 py-3">
                  <span
                    className={`px-2 py-1 rounded text-xs ${
                      log.status === 'success'
                        ? 'bg-green-100 text-green-700'
                        : log.status === 'failed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {log.status}
                  </span>
                </td>
                <td className="px-4 py-3">{log.stocks_count || '-'}</td>
                <td className="px-4 py-3 text-gray-700">{log.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
