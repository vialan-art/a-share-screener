"""插件系统单元测试。"""
import pytest

from backend.plugins.registry import registry
from backend.plugins.adapter import PluginAdapter
from backend.plugins.indicators import MACDPlugin, KDJPlugin, RSIPlugin
from backend.plugins.patterns import HammerPlugin, EngulfingPlugin
from backend.plugins.strategies import VolumeBreakoutPlugin


@pytest.fixture(autouse=True)
def ensure_plugins_loaded():
    """确保测试前所有内置插件已注册。"""
    # plugins/__init__.py 会自动加载；这里不做额外清理
    pass


def test_plugins_registered():
    names = registry.list_plugins()
    assert "macd_golden_cross" in names
    assert "kdj" in names
    assert "rsi_14" in names
    assert "hammer" in names
    assert "engulfing" in names
    assert "volume_breakout" in names


def test_macd_plugin():
    plugin = MACDPlugin()
    # 构造一个简单上涨趋势
    ohlcv = [{"close": 10.0 + i * 0.1} for i in range(40)]
    result = plugin.compute("000001", {}, ohlcv)
    assert result.symbol == "000001"
    assert result.signal_type == "indicator"
    assert "dif" in result.value
    assert result.score is not None


def test_kdj_plugin():
    plugin = KDJPlugin()
    ohlcv = [{"high": 11.0 + i * 0.05, "low": 9.0 + i * 0.05, "close": 10.0 + i * 0.05} for i in range(20)]
    result = plugin.compute("000001", {}, ohlcv)
    assert result.value["k"] >= 0
    assert result.value["k"] <= 100


def test_rsi_plugin():
    plugin = RSIPlugin()
    # 连续下跌，RSI 应较低
    ohlcv = [{"close": 100.0 - i * 1.0} for i in range(20)]
    result = plugin.compute("000001", {}, ohlcv)
    assert result.value < 50


def test_hammer_plugin():
    plugin = HammerPlugin()
    # 正常 K 线序列，最后一天不是锤子
    ohlcv = [
        {"open": 10, "high": 11, "low": 9, "close": 10.2}
        for _ in range(10)
    ]
    result = plugin.compute("000001", {}, ohlcv)
    assert result.passed is False


def test_engulfing_plugin():
    plugin = EngulfingPlugin()
    ohlcv = [
        {"open": 10, "high": 11, "low": 9, "close": 9.5},   # 阴线
        {"open": 9.3, "high": 10.5, "low": 9, "close": 10.5},  # 阳线吞没
    ]
    result = plugin.compute("000001", {}, ohlcv)
    assert result.value["bullish"] is True
    assert result.passed is True


def test_volume_breakout_plugin():
    plugin = VolumeBreakoutPlugin()
    base = [{"close": 10.0, "volume": 1000.0} for _ in range(20)]
    base[-1]["close"] = 11.0
    base[-1]["volume"] = 3000.0
    base[-2]["close"] = 10.0
    result = plugin.compute("000001", {}, base)
    assert result.passed is True
    assert result.score > 0


def test_adapter_aggregate():
    adapter = PluginAdapter()
    metrics = {"roe": 15.0, "profit_growth": 20.0}
    ohlcv = [
        {"open": 10, "high": 11, "low": 9, "close": 9.5, "volume": 1000}
        for _ in range(40)
    ]
    ohlcv[-1]["close"] = 11.0
    ohlcv[-1]["volume"] = 3000.0
    enriched = adapter.enrich_metrics("000001", metrics, ohlcv)
    assert "_plugin_signals" in enriched
    assert "plugin_macd_golden_cross_score" in enriched or "plugin_rsi_14_score" in enriched
    score = adapter.aggregate_technical_score(enriched)
    assert 0 <= score <= 1


def test_scoring_engine_with_plugins():
    from backend.scoring.engine import ScoringEngine
    engine = ScoringEngine()
    stocks = [{"symbol": "000001", "name": "平安银行"}]
    metrics_map = {
        "000001": {
            "roe": 15.0,
            "pe_ttm": 10.0,
            "pb": 1.0,
            "turnover": 2.0,
            "_plugin_signals": {
                "macd_golden_cross": {
                    "name": "macd_golden_cross",
                    "signal_type": "indicator",
                    "score": 1.0,
                    "passed": True,
                    "value": {},
                }
            },
        }
    }
    results = engine.score_batch(stocks, metrics_map)
    assert len(results) == 1
    assert results[0].total_score > 0
    assert "technical" in results[0].details
