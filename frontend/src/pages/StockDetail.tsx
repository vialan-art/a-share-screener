import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchStockDetail } from '../services/api'

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>()
  const [data, setData] = useState<any>(null)

  useEffect(() => {
    if (symbol) {
      fetchStockDetail(symbol).then(setData)
    }
  }, [symbol])

  if (!data) return <div className="p-8">加载中...</div>

  const metrics = data.metrics || {}
  const score = data.score || {}

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link to="/screener" className="text-blue-600 hover:underline">← 返回股票池</Link>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-2xl font-bold">{data.name} ({data.symbol})</h2>
        <p className="text-gray-500">{data.industry} · {data.market}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">评分</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span>综合得分</span>
              <span className="font-bold">{score.total?.toFixed(3) || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span>质量分</span>
              <span>{score.quality?.toFixed(3) || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span>估值分</span>
              <span>{score.value?.toFixed(3) || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span>动量分</span>
              <span>{score.momentum?.toFixed(3) || '-'}</span>
            </div>
            <div className="flex justify-between">
              <span>通过过滤</span>
              <span className={score.passed_filters ? 'text-green-600' : 'text-red-600'}>
                {score.passed_filters ? '是' : '否'}
              </span>
            </div>
            {score.filter_reasons && score.filter_reasons !== '[]' && (
              <div className="text-sm text-red-600 bg-red-50 p-3 rounded">
                {score.filter_reasons}
              </div>
            )}
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">关键财务指标</h3>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries({
              'ROE (%)': metrics.roe,
              'ROA (%)': metrics.roa,
              '毛利率 (%)': metrics.gross_margin,
              '净利率 (%)': metrics.net_margin,
              '营收增长 (%)': metrics.revenue_growth,
              '净利润增长 (%)': metrics.profit_growth,
              '资产负债率 (%)': metrics.debt_to_asset,
              '流动比率': metrics.current_ratio,
              'PE TTM': metrics.pe_ttm,
              'PB': metrics.pb,
              '股息率 (%)': metrics.dividend_yield,
              '审计意见': metrics.audit_opinion,
            }).map(([label, value]) => (
              <div key={label} className="border-b pb-2">
                <p className="text-xs text-gray-500">{label}</p>
                <p className="font-medium">{value !== null && value !== undefined ? (typeof value === 'number' ? value.toFixed(2) : value) : '-'}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
