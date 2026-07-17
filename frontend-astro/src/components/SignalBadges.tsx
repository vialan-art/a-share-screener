export function formatSignalName(name: string): string {
  const map: Record<string, string> = {
    macd_golden_cross: 'MACD金叉', kdj: 'KDJ', rsi_14: 'RSI', bollinger: '布林',
    ma_bullish_alignment: '均线多头', atr_14: 'ATR', hammer: '锤子线', engulfing: '吞没',
    doji: '十字星', morning_star: '启明星', volume_breakout: '放量突破',
    platform_breakout: '平台突破', turtle_breakout_20: '海龟20日', low_atr_growth: '低波动',
    pullback_yearly_ma: '年线回踩', rps_breakout_120: 'RPS120', limit_up_shakeout: '涨停洗盘',
    uptrend_limit_down: '趋势跌停', high_tight_flag: '高位旗形', ma_volume_golden_cross: '量价金叉',
    turtle_trade_enhanced: '海龟增强', stock_scanner_fundamental: '基本面', stock_scanner_sentiment: '情绪面',
  }
  return map[name] || name
}

export function SignalBadges({ signals, max = 3 }: { signals?: Record<string, any> | null; max?: number }) {
  if (!signals) return <span className="text-slate-700 text-xs">—</span>
  const passed = Object.values(signals).filter((s: any) => s.passed === true)
  if (passed.length === 0) return <span className="text-slate-700 text-xs">—</span>
  return (
    <div className="flex flex-wrap gap-1">
      {passed.slice(0, max).map((s: any) => (
        <span
          key={s.name}
          title={s.reason || s.name}
          className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-400/10 text-cyan-300 border border-cyan-400/20 whitespace-nowrap"
        >
          {formatSignalName(s.name)}
        </span>
      ))}
      {passed.length > max && (
        <span className="text-[9px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
          +{passed.length - max}
        </span>
      )}
    </div>
  )
}
