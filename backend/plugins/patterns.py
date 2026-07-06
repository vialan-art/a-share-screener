"""K 线形态识别插件（纯 pandas 实现，无 TA-Lib 依赖）。

思路参考 InStock 的 pattern_recognitions.py，但只保留最经典、解释性最强的几种形态。
"""
from typing import Any, Dict, List

from backend.plugins.base import BaseSignalPlugin, SignalResult
from backend.plugins.registry import register_plugin


class _PatternPlugin(BaseSignalPlugin):
    signal_type = "pattern"

    def _validate_ohlc(self, ohlcv: list) -> "pd.DataFrame":
        if not ohlcv or len(ohlcv) < 2:
            return None
        import pandas as pd
        df = pd.DataFrame(ohlcv)
        for col in ["open", "high", "low", "close"]:
            if col not in df.columns:
                return None
            df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[["open", "high", "low", "close"]].isnull().any().any():
            return None
        return df


@register_plugin
class HammerPlugin(_PatternPlugin):
    """锤子线：下影线长、实体小，出现在下跌趋势末端。"""

    name = "hammer"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._validate_ohlc(ohlcv)
        if df is None or len(df) < 5:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足或字段缺失")

        row = df.iloc[-1]
        body = abs(row["close"] - row["open"])
        lower_shadow = min(row["close"], row["open"]) - row["low"]
        upper_shadow = row["high"] - max(row["close"], row["open"])
        total_range = row["high"] - row["low"]
        if total_range == 0:
            return SignalResult(symbol, self.name, self.signal_type, False, score=0.0, reason="无波动")

        # 下跌趋势：最近5天总体下跌
        downtrend = df["close"].iloc[-1] < df["close"].iloc[-5]
        is_hammer = (lower_shadow >= 2 * body) and (upper_shadow <= body) and (body / total_range <= 0.3)
        detected = bool(is_hammer and downtrend)

        return SignalResult(
            symbol, self.name, self.signal_type, detected,
            score=1.0 if detected else 0.0,
            passed=detected,
            reason="出现锤子线" if detected else "未出现锤子线",
            meta={"body": round(body, 3), "lower_shadow": round(lower_shadow, 3)},
        )


@register_plugin
class EngulfingPlugin(_PatternPlugin):
    """吞没形态：当前 K 线完全包住前一根，且方向相反。"""

    name = "engulfing"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._validate_ohlc(ohlcv)
        if df is None or len(df) < 2:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        prev = df.iloc[-2]
        curr = df.iloc[-1]

        prev_bull = prev["close"] > prev["open"]
        curr_bull = curr["close"] > curr["open"]

        bullish_engulfing = (
            not prev_bull and curr_bull
            and curr["open"] < prev["close"]
            and curr["close"] > prev["open"]
        )
        bearish_engulfing = (
            prev_bull and not curr_bull
            and curr["open"] > prev["close"]
            and curr["close"] < prev["open"]
        )

        detected = bool(bullish_engulfing)
        return SignalResult(
            symbol, self.name, self.signal_type,
            {"bullish": bool(bullish_engulfing), "bearish": bool(bearish_engulfing)},
            score=1.0 if bullish_engulfing else (0.0 if bearish_engulfing else 0.5),
            passed=detected,
            reason="看涨吞没" if bullish_engulfing else ("看跌吞没" if bearish_engulfing else "无吞没"),
        )


@register_plugin
class DojiPlugin(_PatternPlugin):
    """十字星：开盘价与收盘价几乎相同。"""

    name = "doji"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._validate_ohlc(ohlcv)
        if df is None:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        row = df.iloc[-1]
        body = abs(row["close"] - row["open"])
        total_range = row["high"] - row["low"]
        if total_range == 0:
            return SignalResult(symbol, self.name, self.signal_type, False, score=0.5, reason="无波动")

        is_doji = body / total_range < 0.1
        return SignalResult(
            symbol, self.name, self.signal_type, bool(is_doji),
            score=0.5,  # 十字星本身中性
            passed=False,
            reason="十字星" if is_doji else "非十字星",
        )


@register_plugin
class MorningStarPlugin(_PatternPlugin):
    """早晨之星（简化版）：长阴 -> 小实体 -> 长阳，且第三日收盘价深入第一日实体。"""

    name = "morning_star"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._validate_ohlc(ohlcv)
        if df is None or len(df) < 3:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        a_body = a["open"] - a["close"]  # 阴线
        c_body = c["close"] - c["open"]  # 阳线
        b_body = abs(b["close"] - b["open"])
        a_range = a["high"] - a["low"]

        if a_body <= 0 or c_body <= 0 or a_range == 0:
            return SignalResult(symbol, self.name, self.signal_type, False, score=0.0, reason="形态不符")

        long_black = a_body / a_range > 0.5
        small_middle = b_body / a_body < 0.3
        long_white = c_body / a_body > 0.5
        penetrate = c["close"] > (a["open"] + a["close"]) / 2

        detected = bool(long_black and small_middle and long_white and penetrate)
        return SignalResult(
            symbol, self.name, self.signal_type, detected,
            score=1.0 if detected else 0.0,
            passed=detected,
            reason="早晨之星" if detected else "非早晨之星",
        )
