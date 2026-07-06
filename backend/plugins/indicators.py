"""技术指标插件（纯 pandas/numpy，避免 TA-Lib 系统依赖）。

思路参考 InStock 的指标计算，但只保留最常用、最稳定的几个，用原生 pandas 实现。
"""
from typing import Any, Dict, List, Optional

from backend.plugins.base import BaseSignalPlugin, SignalResult
from backend.plugins.registry import register_plugin


class _IndicatorPlugin(BaseSignalPlugin):
    """指标插件公共辅助。"""

    signal_type = "indicator"

    def _get_close(self, ohlcv: list) -> Optional[List[float]]:
        if not ohlcv:
            return None
        closes = []
        for row in ohlcv:
            v = self._safe_float(row.get("close"))
            if v is None:
                return None
            closes.append(v)
        return closes


@register_plugin
class MACDPlugin(_IndicatorPlugin):
    """MACD 指标：DIF 上穿 DEA 为多头信号。"""

    name = "macd_golden_cross"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        closes = self._get_close(ohlcv)
        if closes is None or len(closes) < 35:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        import pandas as pd
        s = pd.Series(closes)
        ema12 = s.ewm(span=12, adjust=False).mean()
        ema26 = s.ewm(span=26, adjust=False).mean()
        dif = ema12 - ema26
        dea = dif.ewm(span=9, adjust=False).mean()
        macd = (dif - dea) * 2

        golden = dif.iloc[-2] <= dea.iloc[-2] and dif.iloc[-1] > dea.iloc[-1]
        value = {
            "dif": round(float(dif.iloc[-1]), 4),
            "dea": round(float(dea.iloc[-1]), 4),
            "macd": round(float(macd.iloc[-1]), 4),
            "golden_cross": bool(golden),
        }
        score = 1.0 if golden else 0.0
        return SignalResult(
            symbol, self.name, self.signal_type, value,
            score=score,
            passed=golden,
            reason="MACD 金叉" if golden else "MACD 未金叉",
        )


@register_plugin
class KDJPlugin(_IndicatorPlugin):
    """KDJ 指标：K < 20 超卖，K > 80 超买。"""

    name = "kdj"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        if not ohlcv or len(ohlcv) < 9:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        import pandas as pd
        df = pd.DataFrame(ohlcv)
        for col in ["high", "low", "close"]:
            if col not in df.columns:
                return SignalResult(symbol, self.name, self.signal_type, None, reason="缺少 OHLC 字段")
            df[col] = pd.to_numeric(df[col], errors="coerce")

        n = 9
        low_min = df["low"].rolling(window=n, min_periods=n).min()
        high_max = df["high"].rolling(window=n, min_periods=n).max()
        rsv = (df["close"] - low_min) / (high_max - low_min) * 100
        k = rsv.ewm(com=2, adjust=False).mean()
        d = k.ewm(com=2, adjust=False).mean()
        j = 3 * k - 2 * d

        kv = float(k.iloc[-1])
        dv = float(d.iloc[-1])
        jv = float(j.iloc[-1])
        oversold = kv < 20
        overbought = kv > 80

        # 评分：超卖区域得分高（潜在反弹），超买得分低
        if kv <= 20:
            score = 1.0
        elif kv >= 80:
            score = 0.0
        else:
            score = 1.0 - (kv - 20) / 60

        return SignalResult(
            symbol, self.name, self.signal_type,
            {"k": round(kv, 2), "d": round(dv, 2), "j": round(jv, 2)},
            score=round(score, 4),
            passed=oversold,
            reason="KDJ 超卖" if oversold else ("KDJ 超买" if overbought else "KDJ 中性"),
        )


@register_plugin
class RSIPlugin(_IndicatorPlugin):
    """RSI(14)：低于30视为超卖，高于70视为超买。"""

    name = "rsi_14"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        closes = self._get_close(ohlcv)
        if closes is None or len(closes) < 15:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        import pandas as pd
        s = pd.Series(closes)
        delta = s.diff()
        gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        v = float(rsi.iloc[-1])

        if v <= 30:
            score = 1.0
            passed = True
            reason = "RSI 超卖"
        elif v >= 70:
            score = 0.0
            passed = False
            reason = "RSI 超买"
        else:
            score = 1.0 - (v - 30) / 40
            passed = False
            reason = "RSI 中性"

        return SignalResult(symbol, self.name, self.signal_type, round(v, 2), score=round(score, 4), passed=passed, reason=reason)


@register_plugin
class BollingerPlugin(_IndicatorPlugin):
    """布林带：价格跌破下轨为超卖，突破上轨为超买。"""

    name = "bollinger"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        closes = self._get_close(ohlcv)
        if closes is None or len(closes) < 20:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        import pandas as pd
        s = pd.Series(closes)
        ma20 = s.rolling(window=20).mean()
        std = s.rolling(window=20).std()
        upper = ma20 + 2 * std
        lower = ma20 - 2 * std

        price = s.iloc[-1]
        ub = upper.iloc[-1]
        lb = lower.iloc[-1]
        mb = ma20.iloc[-1]

        below_lower = price < lb
        above_upper = price > ub
        score = 1.0 if below_lower else (0.0 if above_upper else 0.5)

        return SignalResult(
            symbol, self.name, self.signal_type,
            {"upper": round(float(ub), 3), "middle": round(float(mb), 3), "lower": round(float(lb), 3), "close": round(float(price), 3)},
            score=round(score, 4),
            passed=below_lower,
            reason="跌破布林下轨" if below_lower else ("突破布林上轨" if above_upper else "布林带内"),
        )


@register_plugin
class MABullPlugin(_IndicatorPlugin):
    """均线多头排列：5 > 10 > 20 > 60。"""

    name = "ma_bullish_alignment"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        closes = self._get_close(ohlcv)
        if closes is None or len(closes) < 60:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        import pandas as pd
        s = pd.Series(closes)
        ma5 = s.rolling(window=5).mean().iloc[-1]
        ma10 = s.rolling(window=10).mean().iloc[-1]
        ma20 = s.rolling(window=20).mean().iloc[-1]
        ma60 = s.rolling(window=60).mean().iloc[-1]

        aligned = ma5 > ma10 > ma20 > ma60
        score = 1.0 if aligned else 0.0
        return SignalResult(
            symbol, self.name, self.signal_type,
            {"ma5": round(float(ma5), 3), "ma10": round(float(ma10), 3), "ma20": round(float(ma20), 3), "ma60": round(float(ma60), 3)},
            score=score,
            passed=aligned,
            reason="均线多头排列" if aligned else "均线未多头排列",
        )


@register_plugin
class ATRPlugin(_IndicatorPlugin):
    """ATR(14)：波动率指标，低 ATR 表示走势稳定。"""

    name = "atr_14"

    def compute(self, symbol: str, metrics: Dict[str, Any], ohlcv: List[Dict] = None) -> SignalResult:
        if not ohlcv or len(ohlcv) < 15:
            return SignalResult(symbol, self.name, self.signal_type, None, reason="K线数据不足")

        import pandas as pd
        df = pd.DataFrame(ohlcv)
        for col in ["high", "low", "close"]:
            if col not in df.columns:
                return SignalResult(symbol, self.name, self.signal_type, None, reason="缺少 OHLC 字段")
            df[col] = pd.to_numeric(df[col], errors="coerce")

        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift(1)).abs()
        lc = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        atr = tr.rolling(window=14, min_periods=14).mean().iloc[-1]
        close = df["close"].iloc[-1]
        ratio = atr / close if close > 0 else None

        # 低波动得分高；ratio < 2% 得 1 分，>5% 得 0 分
        if ratio is None:
            score = 0.5
        elif ratio <= 0.02:
            score = 1.0
        elif ratio >= 0.05:
            score = 0.0
        else:
            score = 1.0 - (ratio - 0.02) / 0.03

        return SignalResult(
            symbol, self.name, self.signal_type,
            {"atr": round(float(atr), 4), "atr_to_close": round(ratio, 4) if ratio else None},
            score=round(score, 4),
            passed=ratio is not None and ratio < 0.03,
            reason="波动率较低" if (ratio and ratio < 0.03) else "波动率偏高",
        )
