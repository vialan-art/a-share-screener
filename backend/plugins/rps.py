"""批量计算 RPS 相对强度。

Sequoia-X 的 RPS 策略需要全市场截面排名。这里提供独立函数，
输入一组股票的 OHLCV 数据，输出每只股票的 rps_120 字段。
"""
from typing import Dict, List

import pandas as pd


def calculate_rps(
    ohlcv_map: Dict[str, List[Dict]],
    period: int = 120,
    price_col: str = "close",
) -> Dict[str, float]:
    """计算一组股票在最新截面的 RPS 排名。

    Args:
        ohlcv_map: {symbol: [ohlcv records]}，每条记录需含 price_col 和 trade_date
        period: 回看周期，默认 120 日
        price_col: 价格列名

    Returns:
        {symbol: rps_score}，rps_score 范围 0-100
    """
    pct_changes = {}
    latest_dates = {}

    for symbol, ohlcv in ohlcv_map.items():
        if not ohlcv or len(ohlcv) < period + 1:
            continue
        df = pd.DataFrame(ohlcv)
        if price_col not in df.columns:
            continue
        df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
        df = df.dropna(subset=[price_col])
        if len(df) < period + 1:
            continue

        latest = df.iloc[-1]
        prev = df.iloc[-(period + 1)]
        if prev[price_col] <= 0:
            continue
        pct_changes[symbol] = (latest[price_col] - prev[price_col]) / prev[price_col]
        latest_dates[symbol] = latest.get("trade_date")

    if not pct_changes:
        return {}

    series = pd.Series(pct_changes)
    rps = series.rank(pct=True) * 100
    return rps.to_dict()
