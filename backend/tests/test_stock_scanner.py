"""stock-scanner 插件单元测试。"""
import pytest

from backend.plugins.stock_scanner import StockScannerFundamentalPlugin, StockScannerSentimentPlugin
from backend.plugins.registry import registry
from backend.plugins.adapter import PluginAdapter
from backend.scoring.engine import ScoringEngine


def test_stock_scanner_plugins_registered():
    names = registry.list_plugins()
    assert "stock_scanner_fundamental" in names
    assert "stock_scanner_sentiment" in names


def test_fundamental_plugin_strong():
    plugin = StockScannerFundamentalPlugin()
    metrics = {
        "roe": 18.0,
        "debt_to_asset": 25.0,
        "revenue_growth": 25.0,
        "profit_growth": 20.0,
        "pe_ttm": 15.0,
        "pb": 1.5,
    }
    result = plugin.compute("000001", metrics)
    assert result.signal_type == "fundamental"
    assert result.score > 0.7
    assert result.passed is True


def test_fundamental_plugin_weak():
    plugin = StockScannerFundamentalPlugin()
    metrics = {
        "roe": 2.0,
        "debt_to_asset": 75.0,
        "revenue_growth": -15.0,
    }
    result = plugin.compute("000001", metrics)
    assert result.score < 0.5
    assert result.passed is False


def test_sentiment_plugin_positive():
    plugin = StockScannerSentimentPlugin()
    news = [
        {"text": "公司业绩增长超预期，龙头地位稳固，券商维持买入评级", "type": "company_news", "weight": 1.0},
        {"text": "签订重大合同，股价有望突破上涨", "type": "announcement", "weight": 1.2},
    ]
    result = plugin.compute("000001", {"_news_data": news})
    assert result.signal_type == "sentiment"
    assert result.score > 0.5
    assert result.passed is True


def test_sentiment_plugin_negative():
    plugin = StockScannerSentimentPlugin()
    news = [
        {"text": "公司亏损扩大，存在退市风险，股价下跌压力大", "type": "company_news", "weight": 1.0},
        {"text": "收到监管处罚，债务危机发酵", "type": "announcement", "weight": 1.2},
    ]
    result = plugin.compute("000001", {"_news_data": news})
    assert result.score < 0.5
    assert result.passed is False


def test_sentiment_plugin_no_news():
    plugin = StockScannerSentimentPlugin()
    result = plugin.compute("000001", {"_news_data": []})
    assert result.score == 0.5
    assert result.passed is False
    assert result.reason == "无新闻数据"


def test_adapter_with_stock_scanner_signals():
    adapter = PluginAdapter()
    metrics = {
        "roe": 18.0,
        "revenue_growth": 25.0,
        "pe_ttm": 15.0,
        "_news_data": [
            {"text": "业绩大增，股价突破新高", "type": "company_news", "weight": 1.0},
        ],
    }
    enriched = adapter.enrich_metrics("000001", metrics)
    assert "_plugin_signals" in enriched
    assert "plugin_stock_scanner_fundamental_score" in enriched
    assert "plugin_stock_scanner_sentiment_score" in enriched
    score = adapter.aggregate_technical_score(enriched)
    assert 0 <= score <= 1


def test_scoring_engine_with_stock_scanner_plugins():
    adapter = PluginAdapter()
    metrics = {
        "roe": 15.0,
        "pe_ttm": 10.0,
        "pb": 1.0,
        "turnover": 2.0,
        "_news_data": [
            {"text": "业绩超预期，机构看好", "type": "company_news", "weight": 1.0},
        ],
    }
    enriched = adapter.enrich_metrics("000001", metrics)

    engine = ScoringEngine()
    stocks = [{"symbol": "000001", "name": "平安银行"}]
    metrics_map = {"000001": enriched}
    results = engine.score_batch(stocks, metrics_map)
    assert len(results) == 1
    assert results[0].total_score > 0
    assert "fundamental" in results[0].details.get("technical", {}) or "sentiment" in results[0].details.get("technical", {}), results[0].details
