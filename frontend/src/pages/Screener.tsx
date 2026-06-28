import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchLatestSnapshot } from '../services/api'

export default function Screener() {
  const [items, setItems] = useState<any[]>([])
  const [date, setDate] = useState('')
  const [minScore, setMinScore] = useState('')
  const [industry, setIndustry] = useState('')

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

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">候选股票池</h2>
        <div className="flex gap-3">
          <input
            type="number"
            placeholder="最低得分"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
          />
          <input
            type="text"
            placeholder="行业筛选"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
          />
          <button
            onClick={loadItems}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            筛选
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-500">快照日期：{date || '无'}</p>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">代码</th>
              <th className="px-4 py-3 text-left">名称</th>
              <th className="px-4 py-3 text-left">行业</th>
              <th className="px-4 py-3 text-right">综合</th>
              <th className="px-4 py-3 text-right">质量</th>
              <th className="px-4 py-3 text-right">估值</th>
              <th className="px-4 py-3 text-right">动量</th>
              <th className="px-4 py-3 text-right">PE</th>
              <th className="px-4 py-3 text-right">PB</th>
              <th className="px-4 py-3 text-right">ROE</th>
              <th className="px-4 py-3 text-right">负债率</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.symbol} className="border-t hover:bg-gray-50">
                <td className="px-4 py-3 font-mono">
                  <Link to={`/stock/${item.symbol}`} className="text-blue-600 hover:underline">
                    {item.symbol}
                  </Link>
                </td>
                <td className="px-4 py-3">{item.name}</td>
                <td className="px-4 py-3">{item.industry}</td>
                <td className="px-4 py-3 text-right font-bold">{item.total_score.toFixed(3)}</td>
                <td className="px-4 py-3 text-right">{item.quality_score.toFixed(3)}</td>
                <td className="px-4 py-3 text-right">{item.value_score.toFixed(3)}</td>
                <td className="px-4 py-3 text-right">{item.momentum_score.toFixed(3)}</td>
                <td className="px-4 py-3 text-right">{item.pe_ttm?.toFixed(2) || '-'}</td>
                <td className="px-4 py-3 text-right">{item.pb?.toFixed(2) || '-'}</td>
                <td className="px-4 py-3 text-right">{item.roe?.toFixed(2) || '-'}</td>
                <td className="px-4 py-3 text-right">{item.debt_to_asset?.toFixed(2) || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
