"""过滤引擎最小单元测试。"""
import pytest
from backend.filters.engine import FilterEngine


def test_filter_passes_healthy_stock():
    engine = FilterEngine()
    stock = {"symbol": "000001", "industry": "银行"}
    metrics = {
        "audit_opinion": "标准无保留意见",
        "roe": 12.0,
        "debt_to_asset": 60.0,
        "interest_bearing_debt_ratio": 40.0,
        "revenue_growth": 10.0,
        "profit_growth": 15.0,
        "operating_cash_flow": 10.0,
        "ocf_to_net_profit": 0.8,
        "pe_ttm": 10.0,
        "pb": 1.2,
    }
    result = engine.evaluate(stock, metrics)
    assert result.passed is True
    assert result.reasons == []


def test_filter_fails_high_debt():
    engine = FilterEngine()
    stock = {"symbol": "000002", "industry": "房地产"}
    metrics = {
        "audit_opinion": "标准无保留意见",
        "roe": 6.0,
        "debt_to_asset": 90.0,
        "interest_bearing_debt_ratio": 70.0,
        "revenue_growth": 5.0,
        "profit_growth": 5.0,
        "operating_cash_flow": 1.0,
        "ocf_to_net_profit": 0.5,
        "pe_ttm": 20.0,
        "pb": 1.0,
    }
    result = engine.evaluate(stock, metrics)
    assert result.passed is False
    assert any("负债" in r for r in result.reasons)


def test_filter_loss_stock_with_ps_allowed():
    engine = FilterEngine()
    stock = {"symbol": "300001", "industry": "电子"}
    metrics = {
        "audit_opinion": "标准无保留意见",
        "roe": 12.0,
        "debt_to_asset": 40.0,
        "interest_bearing_debt_ratio": 25.0,
        "revenue_growth": 20.0,
        "profit_growth": 10.0,
        "operating_cash_flow": 5.0,
        "ocf_to_net_profit": 0.5,
        "pe_ttm": -10.0,
        "ps_ttm": 5.0,
        "pb": 2.0,
    }
    result = engine.evaluate(stock, metrics)
    assert result.passed is True


def test_filter_batch_runs():
    engine = FilterEngine()
    stocks = [
        {"symbol": "A", "industry": "银行"},
        {"symbol": "B", "industry": "食品饮料"},
    ]
    metrics_map = {
        "A": {
            "audit_opinion": "标准无保留意见",
            "roe": 10.0,
            "debt_to_asset": 50.0,
            "interest_bearing_debt_ratio": 30.0,
            "revenue_growth": 5.0,
            "profit_growth": 5.0,
            "operating_cash_flow": 1.0,
            "ocf_to_net_profit": 0.5,
            "pe_ttm": 8.0,
            "pb": 1.0,
        },
        "B": {
            "audit_opinion": "标准无保留意见",
            "roe": 15.0,
            "debt_to_asset": 30.0,
            "interest_bearing_debt_ratio": 20.0,
            "revenue_growth": 15.0,
            "profit_growth": 20.0,
            "operating_cash_flow": 10.0,
            "ocf_to_net_profit": 1.0,
            "pe_ttm": 25.0,
            "pb": 4.0,
        },
    }
    results = engine.evaluate_batch(stocks, metrics_map)
    assert len(results) == 2
    assert all(r.passed for r in results)
