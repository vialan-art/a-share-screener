import { useEffect, useState } from 'react'
import { fetchLatestSnapshot, fetchLogs, runPipeline, getWatchlistDownloadUrl } from '../services/api'

export default function Overview() {
  const [snapshot, setSnapshot] = useState<any>(null)
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    const [snap, logList] = await Promise.all([
      fetchLatestSnapshot(),
      fetchLogs(),
    ])
    setSnapshot(snap)
    setLogs(logList)
  }

  async function handleRun() {
    setLoading(true)
    await runPipeline()
    await loadData()
    setLoading(false)
  }

  const topStocks = snapshot?.items?.slice(0, 5) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">系统概览</h2>
        <div className="flex gap-3">
          <a
            href={getWatchlistDownloadUrl()}
            download
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            导出 CSV Watchlist
          </a>
          <button
            onClick={handleRun}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? '运行中...' : '手动运行选股'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm text-gray-500">最新快照日期</p>
          <p className="text-2xl font-bold">{snapshot?.date || '无'}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm text-gray-500">候选股票数</p>
          <p className="text-2xl font-bold">{snapshot?.count || 0}</p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm text-gray-gray-500">最高分</p>
          <p className="text-2xl font-bold">
            {snapshot?.items?.[0]?.total_score?.toFixed(3) || '-'}
          </p>
        </div>
        <div className="bg-white p-4 rounded-lg shadow">
          <p className="text-sm text-gray-500">最近更新</p>
          <p className="text-sm font-medium">{logs[0]?.time || '-'}</p>
          <p className={`text-xs ${logs[0]?.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {logs[0]?.status || '-'}
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-4">今日 TOP 5</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left">代码</th>
                <th className="px-4 py-2 text-left">名称</th>
                <th className="px-4 py-2 text-left">行业</th>
                <th className="px-4 py-2 text-right">综合得分</th>
                <th className="px-4 py-2 text-right">质量分</th>
                <th className="px-4 py-2 text-right">估值分</th>
                <th className="px-4 py-2 text-right">动量分</th>
              </tr>
            </thead>
            <tbody>
              {topStocks.map((item: any) => (
                <tr key={item.symbol} className="border-t">
                  <td className="px-4 py-2 font-mono">{item.symbol}</td>
                  <td className="px-4 py-2">{item.name}</td>
                  <td className="px-4 py-2">{item.industry}</td>
                  <td className="px-4 py-2 text-right font-bold">{item.total_score.toFixed(3)}</td>
                  <td className="px-4 py-2 text-right">{item.quality_score.toFixed(3)}</td>
                  <td className="px-4 py-2 text-right">{item.value_score.toFixed(3)}</td>
                  <td className="px-4 py-2 text-right">{item.momentum_score.toFixed(3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
