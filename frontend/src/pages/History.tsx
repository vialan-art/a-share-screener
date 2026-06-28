import { useEffect, useState } from 'react'
import { fetchSnapshotDates, fetchSnapshotByDate } from '../services/api'

export default function History() {
  const [dates, setDates] = useState<string[]>([])
  const [selectedDate, setSelectedDate] = useState('')
  const [items, setItems] = useState<any[]>([])

  useEffect(() => {
    fetchSnapshotDates().then((d) => {
      setDates(d)
      if (d.length > 0) {
        setSelectedDate(d[0])
      }
    })
  }, [])

  useEffect(() => {
    if (selectedDate) {
      fetchSnapshotByDate(selectedDate).then((data) => setItems(data.items || []))
    }
  }, [selectedDate])

  return (
    <div className="space-y-4">
      <h2 className="text-2xl font-bold">历史存档</h2>

      <div className="flex gap-2">
        {dates.map((date) => (
          <button
            key={date}
            onClick={() => setSelectedDate(date)}
            className={`px-3 py-1 rounded-lg text-sm ${
              selectedDate === date
                ? 'bg-blue-600 text-white'
                : 'bg-white border hover:bg-gray-50'
            }`}
          >
            {date}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">代码</th>
              <th className="px-4 py-3 text-left">名称</th>
              <th className="px-4 py-3 text-left">行业</th>
              <th className="px-4 py-3 text-right">综合得分</th>
              <th className="px-4 py-3 text-right">PE</th>
              <th className="px-4 py-3 text-right">PB</th>
              <th className="px-4 py-3 text-right">ROE</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.symbol} className="border-t">
                <td className="px-4 py-3 font-mono">{item.symbol}</td>
                <td className="px-4 py-3">{item.name}</td>
                <td className="px-4 py-3">{item.industry}</td>
                <td className="px-4 py-3 text-right font-bold">{item.total_score.toFixed(3)}</td>
                <td className="px-4 py-3 text-right">{item.pe_ttm?.toFixed(2) || '-'}</td>
                <td className="px-4 py-3 text-right">{item.pb?.toFixed(2) || '-'}</td>
                <td className="px-4 py-3 text-right">{item.roe?.toFixed(2) || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
