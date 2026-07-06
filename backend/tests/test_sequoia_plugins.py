"""Sequoia-X 策略插件单元测试。"""
import pytest

from backend.plugins.sequoia_strategies import (
    RPSBreakoutPlugin,
    LimitUpShakeoutPlugin,
    UptrendLimitDownPlugin,
    HighTightFlagPlugin,
    MAVolumeCrossPlugin,
    TurtleTradeEnhancedPlugin,
)
from backend.plugins.rps import calculate_rps
from backend.plugins.adapter import PluginAdapter


def _ohlcv_uptrend(n: int = 130, start: float = 10.0):
    """生成简单上涨趋势 OHLCV。"""
    ohlcv = []
    close = start
    for i in range(n):
        open_p = close
        close *= 1.005
        high = close * 1.01
        low = open_p * 0.99
        ohlcv.append({
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "volume": 1000 + i * 10,
            "amount": (1000 + i * 10) * close,
        })
    return ohlcv


def test_rps_breakout():
    plugin = RPSBreakoutPlugin()
    ohlcv = _ohlcv_uptrend(130)
    result = plugin.compute("000001", {"rps_120": 95.0}, ohlcv)
    assert result.passed is True
    assert result.score == 1.0


def test_limit_up_shakeout():
    plugin = LimitUpShakeoutPlugin()
    ohlcv = _ohlcv_uptrend(10)
    # 人为构造涨停洗盘形态
    ohlcv[-3]["close"] = 10.0
    ohlcv[-2]["close"] = 10.95  # 涨停
    ohlcv[-2]["open"] = 10.0
    ohlcv[-2]["high"] = 10.95
    ohlcv[-2]["low"] = 10.0
    ohlcv[-2]["volume"] = 1000
    ohlcv[-1]["open"] = 10.90
    ohlcv[-1]["close"] = 10.50  # 收阴
    ohlcv[-1]["high"] = 11.00
    ohlcv[-1]["low"] = 10.95    # 不破昨收（等于昨收）
    ohlcv[-1]["volume"] = 3000  # 放量
    result = plugin.compute("000001", {}, ohlcv)
    assert result.passed is True
    assert result.score == 1.0


def test_uptrend_limit_down():
    plugin = UptrendLimitDownPlugin()
    ohlcv = _ohlcv_uptrend(70)
    ohlcv[-1]["close"] = ohlcv[-2]["close"] * 0.90  # 跌停
    ohlcv[-1]["volume"] = ohlcv[-2]["volume"] * 3   # 放量
    result = plugin.compute("000001", {}, ohlcv)
    assert result.passed is True


def test_high_tight_flag():
    plugin = HighTightFlagPlugin()
    ohlcv = []
    for i in range(50):
        ohlcv.append({
            "close": 10.0 + i * 0.25,
            "high": (10.0 + i * 0.25) * 1.01,
            "low": (10.0 + i * 0.25) * 0.99,
            "volume": 1000,
        })
    # 近 10 日横盘缩量
    base = ohlcv[-10]["close"]
    for i in range(10):
        ohlcv[-10 + i]["close"] = base + i * 0.01
        ohlcv[-10 + i]["high"] = base + 0.05
        ohlcv[-10 + i]["low"] = base - 0.05
        ohlcv[-10 + i]["volume"] = 100
    ohlcv[-1]["volume"] = 50
    result = plugin.compute("000001", {}, ohlcv)
    assert result.passed is True


def test_ma_volume_golden_cross():
    plugin = MAVolumeCrossPlugin()
    # 构造精确序列：前 80 日 close=10 让 ma20=10，前 3 日下跌让 ma5<ma20，最后 2 日大涨使 ma5 金叉
    closes = [10.0] * 80 + [9.8, 9.4, 9.0, 11.0, 13.0]
    volumes = [1000] * 80 + [1000, 1000, 1000, 1000, 10000]
    ohlcv = [{"close": c, "volume": v} for c, v in zip(closes, volumes)]
    result = plugin.compute("000001", {}, ohlcv)
    assert result.passed is True


def test_turtle_trade_enhanced():
    plugin = TurtleTradeEnhancedPlugin()
    ohlcv = _ohlcv_uptrend(25)
    ohlcv[-1]["close"] = max(r["high"] for r in ohlcv[:-1]) * 1.01
    ohlcv[-1]["open"] = ohlcv[-1]["close"] * 0.99
    ohlcv[-1]["amount"] = 200_000_000
    result = plugin.compute("000001", {}, ohlcv)
    assert result.passed is True


def test_calculate_rps():
    ohlcv_map = {
        "000001": _ohlcv_uptrend(130, start=10.0),
        "000002": _ohlcv_uptrend(130, start=10.0),
        "000003": _ohlcv_uptrend(130, start=20.0),
    }
    rps = calculate_rps(ohlcv_map, period=120)
    assert len(rps) == 3
    assert 0 <= rps["000003"] <= 100
    # 从 20 涨到最高，涨幅应该最大
    assert rps["000003"] >= rps["000001"]


def test_adapter_with_rps():
    stocks = [{"symbol": "000001"}, {"symbol": "000002"}, {"symbol": "000003"}]
    ohlcv_map = {
        "000001": _ohlcv_uptrend(130, start=10.0),
        "000002": _ohlcv_uptrend(130, start=15.0),
        "000003": _ohlcv_uptrend(130, start=20.0),
    }
    adapter = PluginAdapter()
    enriched = adapter.enrich_batch(stocks, {}, ohlcv_map)
    assert "rps_120" in enriched["000001"]
    assert "plugin_rps_breakout_120_score" in enriched["000001"]

    # 涨幅最大的应该 rps 最高
    assert enriched["000003"]["rps_120"] >= enriched["000001"]["rps_120"]
