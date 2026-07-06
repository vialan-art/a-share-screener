"""Sequoia-X 策略插件化：把其 A 股特色策略适配到统一插件接口。

设计原则：
1. 只复用计算逻辑，不依赖 Sequoia-X 的 DataEngine/Settings/飞书推送。
2. 单只股票输入 OHLCV，输出 SignalResult。
3. RPS 需要全市场截面数据，因此提供单独的 batch_rps 函数；单只股票的 rps_breakout 插件
   接收预计算的 rps 字段。
"""
from typing import Any, Dict, List, Optional

import pandas as pd

from backend.plugins.base import BaseSignalPlugin, SignalResult
from backend.plugins.registry import register_plugin


class _SequoiaPlugin(BaseSignalPlugin):
    """Sequoia 策略公共辅助。"""

    signal_type = "strategy"

    def _df(self, ohlcv: list) -> Optional[pd.DataFrame]:
        if not ohlcv or len(ohlcv) < 3:
            return None
        df = pd.DataFrame(ohlcv)
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        # 最少需要 close 和 volume
        if df[["close", "volume"]].isnull().any().any():
            return None
        return df


@register_plugin
class RPSBreakoutPlugin(_SequoiaPlugin):
    """RPS 极强动量突破：120 日涨幅排名前 90%，且收盘价接近 120 日高点。

    注意：单只股票需要预计算 rps_120 字段（由外部批量计算后传入 metrics）。
    """

    name = "rps_breakout_120"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._df(ohlcv)
        if df is None or len(df) < 120:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足 120 日")

        rps = self._safe_float(metrics.get("rps_120"))
        if rps is None:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="缺少 rps_120 字段")

        high120 = df["high"].iloc[-121:-1].max()
        close = df["close"].iloc[-1]
        if pd.isna(high120) or high120 == 0:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="数据无效")

        near_high = close >= high120 * 0.90
        strong = rps >= 90
        triggered = strong and near_high

        return SignalResult(
            symbol, self.name, self.signal_type,
            {"rps_120": round(rps, 2), "high_120": round(float(high120), 3), "close": round(float(close), 3)},
            score=1.0 if triggered else (0.5 if strong else 0.0),
            passed=triggered,
            reason="RPS 极强动量突破" if triggered else ("RPS 强势但未突破" if strong else "RPS 未进入前 10%"),
        )


@register_plugin
class LimitUpShakeoutPlugin(_SequoiaPlugin):
    """涨停洗盘：昨日涨停，今日放量收阴但最低价不破昨收。"""

    name = "limit_up_shakeout"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._df(ohlcv)
        if df is None or len(df) < 3:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        prev2 = df.iloc[-3]
        prev1 = df.iloc[-2]
        today = df.iloc[-1]

        limit_up = prev1["close"] >= prev2["close"] * 1.095
        bearish = today["close"] < today["open"]
        volume_surge = today["volume"] > prev1["volume"] * 2.0
        support = today["low"] >= prev1["close"]

        triggered = limit_up and bearish and volume_surge and support
        return SignalResult(
            symbol, self.name, self.signal_type,
            {
                "yesterday_limit_up": bool(limit_up),
                "today_bearish": bool(bearish),
                "volume_surge": bool(volume_surge),
                "support_hold": bool(support),
            },
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="涨停洗盘" if triggered else "未触发涨停洗盘",
        )


@register_plugin
class UptrendLimitDownPlugin(_SequoiaPlugin):
    """上升趋势跌停：20 日均线 > 60 日均线，今日放量跌停。"""

    name = "uptrend_limit_down"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._df(ohlcv)
        if df is None or len(df) < 60:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足 60 日")

        df["ma20"] = df["close"].rolling(20).mean()
        df["ma60"] = df["close"].rolling(60).mean()
        df["vol_ma20"] = df["volume"].rolling(20).mean()

        prev = df.iloc[-2]
        today = df.iloc[-1]

        if pd.isna(prev["ma20"]) or pd.isna(prev["ma60"]) or pd.isna(today["vol_ma20"]):
            return SignalResult(symbol, self.name, self.signal_type, None, reason="均线/成交量计算失败")

        uptrend = prev["ma20"] > prev["ma60"]
        limit_down = today["close"] <= prev["close"] * 0.905
        volume_surge = today["volume"] > today["vol_ma20"] * 2.0

        triggered = uptrend and limit_down and volume_surge
        return SignalResult(
            symbol, self.name, self.signal_type,
            {"uptrend": bool(uptrend), "limit_down": bool(limit_down), "volume_surge": bool(volume_surge)},
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="上升趋势放量跌停" if triggered else "未触发",
        )


@register_plugin
class HighTightFlagPlugin(_SequoiaPlugin):
    """高窄旗形：40 日涨幅 > 60%，近 10 日振幅 < 15% 且缩量。"""

    name = "high_tight_flag"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._df(ohlcv)
        if df is None or len(df) < 40:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足 40 日")

        tail40 = df.tail(40)
        tail10 = df.tail(10)

        high40 = tail40["high"].max()
        low40 = tail40["low"].min()
        high10 = tail10["high"].max()
        low10 = tail10["low"].min()

        if low40 == 0 or low10 == 0:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="价格无效")

        momentum = high40 / low40 > 1.6
        consolidation = high10 / low10 < 1.15
        high_level = low10 >= high40 * 0.8
        vol_ma20 = df["volume"].iloc[-21:-1].mean()
        shrink = df["volume"].iloc[-1] < vol_ma20 * 0.6

        triggered = momentum and consolidation and high_level and shrink
        return SignalResult(
            symbol, self.name, self.signal_type,
            {
                "momentum_40d": round(float(high40 / low40), 3),
                "consolidation_10d": round(float(high10 / low10), 3),
                "volume_shrink": bool(shrink),
            },
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="高窄旗形整理" if triggered else "未触发",
        )


@register_plugin
class MAVolumeCrossPlugin(_SequoiaPlugin):
    """均线放量金叉：5 日均线上穿 20 日均线，且成交量 > 20 日均量 1.5 倍。"""

    name = "ma_volume_golden_cross"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._df(ohlcv)
        if df is None or len(df) < 20:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        df["ma5"] = df["close"].rolling(5).mean()
        df["ma20"] = df["close"].rolling(20).mean()
        df["vol_ma20"] = df["volume"].rolling(20).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        golden = prev["ma5"] < prev["ma20"] and last["ma5"] > last["ma20"]
        volume_surge = last["volume"] > last["vol_ma20"] * 1.5
        triggered = golden and volume_surge

        return SignalResult(
            symbol, self.name, self.signal_type,
            {"golden_cross": bool(golden), "volume_surge": bool(volume_surge)},
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="均线放量金叉" if triggered else "未触发",
        )


@register_plugin
class TurtleTradeEnhancedPlugin(_SequoiaPlugin):
    """Sequoia-X 改良版海龟交易：20 日新高 + 成交额过亿 + 实体阳线 + 真涨。"""

    name = "turtle_trade_enhanced"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        df = self._df(ohlcv)
        if df is None or len(df) < 21:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        # BaoStock 返回的是 amount（元）/ turnover，统一处理
        turnover_col = None
        for col in ["amount", "turnover"]:
            if col in df.columns:
                turnover_col = col
                break
        if turnover_col is None:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="缺少成交额字段")

        df["high_20"] = df["high"].shift(1).rolling(20).max()
        last = df.iloc[-1]
        prev = df.iloc[-2]

        if pd.isna(last["high_20"]):
            return SignalResult(symbol, self.name, self.signal_type, None, reason="滚动最高计算失败")

        turnover = float(last[turnover_col])
        breakout = last["close"] > last["high_20"]
        liquid = turnover > 100_000_000
        yang = last["close"] > last["open"]
        real_up = last["close"] > prev["close"]

        triggered = breakout and liquid and yang and real_up
        return SignalResult(
            symbol, self.name, self.signal_type,
            {
                "breakout": bool(breakout),
                "turnover": round(turnover, 2),
                "yang_line": bool(yang),
                "real_up": bool(real_up),
            },
            score=1.0 if triggered else 0.0,
            passed=triggered,
            reason="海龟交易（增强版）" if triggered else "未触发",
        )
