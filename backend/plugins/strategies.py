"""选股策略插件（思路参考 KHunter）。

每个策略接收 symbol + metrics + ohlcv，输出是否触发及信号分数。
"""
from typing import Any, Dict, List

import pandas as pd

from backend.plugins.base import BaseSignalPlugin, SignalResult
from backend.plugins.registry import register_plugin


class _StrategyPlugin(BaseSignalPlugin):
    signal_type = "strategy"

    def _ohlcv_df(self, ohlcv: list) -> "pd.DataFrame":
        if not ohlcv:
            return None
        import pandas as pd
        df = pd.DataFrame(ohlcv)
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "close" not in df.columns or df["close"].isnull().all():
            return None
        return df


@register_plugin
class VolumeBreakoutPlugin(_StrategyPlugin):
    """放量上涨：当日成交量 > 20 日均量 1.5 倍，且收盘价上涨。"""

    name = "volume_breakout"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._ohlcv_df(ohlcv)
        if df is None or len(df) < 20:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        vol_ma20 = df["volume"].rolling(window=20).mean().iloc[-1]
        today_vol = df["volume"].iloc[-1]
        today_close = df["close"].iloc[-1]
        prev_close = df["close"].iloc[-2]

        if vol_ma20 == 0 or pd.isna(vol_ma20):
            return SignalResult(symbol, self.name, self.signal_type, None, reason="成交量无效")

        volume_ratio = today_vol / vol_ma20
        price_up = today_close > prev_close
        triggered = volume_ratio >= 1.5 and price_up

        score = min(volume_ratio / 2.0, 1.0) if triggered else 0.0
        return SignalResult(
            symbol, self.name, self.signal_type,
            {"volume_ratio": round(float(volume_ratio), 3), "price_up": bool(price_up)},
            score=round(score, 4),
            passed=triggered,
            reason="放量上涨" if triggered else "未放量上涨",
        )


@register_plugin
class MABreakoutPlugin(_StrategyPlugin):
    """突破平台：收盘价创 20 日新高，且成交量放大。"""

    name = "platform_breakout"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._ohlcv_df(ohlcv)
        if df is None or len(df) < 20:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        close = df["close"]
        high20 = close.rolling(window=20).max().iloc[-2]  # 前 20 日最高（不含今日）
        today_close = close.iloc[-1]
        today_vol = df["volume"].iloc[-1]
        vol_ma20 = df["volume"].rolling(window=20).mean().iloc[-1]

        if pd.isna(high20) or high20 == 0 or pd.isna(vol_ma20) or vol_ma20 == 0:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="数据无效")

        breakout = today_close > high20
        volume_expansion = today_vol > vol_ma20 * 1.2
        triggered = breakout and volume_expansion

        score = 1.0 if triggered else 0.0
        return SignalResult(
            symbol, self.name, self.signal_type,
            {"high_20": round(float(high20), 3), "breakout": bool(breakout), "volume_expansion": bool(volume_expansion)},
            score=score,
            passed=triggered,
            reason="突破平台" if triggered else "未突破平台",
        )


@register_plugin
class TurtleBreakoutPlugin(_StrategyPlugin):
    """海龟交易：收盘价突破 20 日最高价。"""

    name = "turtle_breakout_20"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._ohlcv_df(ohlcv)
        if df is None or len(df) < 20:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        high20 = df["high"].rolling(window=20).max().iloc[-2]
        today_close = df["close"].iloc[-1]
        if pd.isna(high20) or high20 == 0:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="数据无效")

        triggered = today_close > high20
        return SignalResult(
            symbol, self.name, self.signal_type,
            {"high_20": round(float(high20), 3)},
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="海龟 20 日突破" if triggered else "未突破",
        )


@register_plugin
class LowATRGrowthPlugin(_StrategyPlugin):
    """低波动成长：ROE > 8%、净利润增长 > 0%、ATR/close < 3%。"""

    name = "low_atr_growth"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        roe = self._safe_float(metrics.get("roe"))
        profit_growth = self._safe_float(metrics.get("profit_growth"))

        df = self._ohlcv_df(ohlcv)
        atr_ok = False
        atr_ratio = None
        if df is not None and len(df) >= 15:
            hl = df["high"] - df["low"]
            hc = (df["high"] - df["close"].shift(1)).abs()
            lc = (df["low"] - df["close"].shift(1)).abs()
            import pandas as pd
            tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
            atr = tr.rolling(window=14, min_periods=14).mean().iloc[-1]
            close = df["close"].iloc[-1]
            atr_ratio = float(atr / close) if close > 0 else None
            atr_ok = atr_ratio is not None and atr_ratio < 0.03

        roe_ok = roe is not None and roe >= 8
        growth_ok = profit_growth is not None and profit_growth > 0
        triggered = roe_ok and growth_ok and atr_ok

        meta = {"roe_ok": roe_ok, "growth_ok": growth_ok, "atr_ratio": round(atr_ratio, 4) if atr_ratio else None}
        return SignalResult(
            symbol, self.name, self.signal_type, meta,
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="低波动成长股" if triggered else "不符合低波动成长条件",
        )


@register_plugin
class PullbackToYearlyMAPlugin(_StrategyPlugin):
    """回踩年线：价格回调到 250 日均线附近（偏离 < 5%），且中长期向上。"""

    name = "pullback_yearly_ma"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._ohlcv_df(ohlcv)
        if df is None or len(df) < 250:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足 250 日")

        close = df["close"]
        ma250 = close.rolling(window=250).mean().iloc[-1]
        today = close.iloc[-1]
        ma60 = close.rolling(window=60).mean().iloc[-1]
        if pd.isna(ma250) or ma250 == 0 or pd.isna(ma60):
            return SignalResult(symbol, self.name, self.signal_type, None, reason="均线计算失败")

        deviation = abs(today - ma250) / ma250
        uptrend = ma60 > ma250
        triggered = deviation < 0.05 and uptrend

        return SignalResult(
            symbol, self.name, self.signal_type,
            {"ma250": round(float(ma250), 3), "deviation": round(float(deviation), 4), "uptrend": bool(uptrend)},
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="回踩年线" if triggered else "未回踩年线",
        )
