"""评分引擎最小单元测试。"""
import pytest
from backend.scoring.engine import ScoringEngine


def test_scoring_ranks_higher_quality():
    engine = ScoringEngine()
    stocks = [
        {"symbol": "A", "industry": "消费"},
        {"symbol": "B", "industry": "消费"},
    ]
    metrics_map = {
        "A": {
            "roe": 20.0,
            "gross_margin": 40.0,
            "net_margin": 15.0,
            "profit_growth": 30.0,
            "ocf_to_net_profit": 1.2,
            "pe_ttm": 10.0,
            "pb": 1.5,
            "turnover": 2.0,
            "revenue_growth": 20.0,
        },
        "B": {
            "roe": 5.0,
            "gross_margin": 15.0,
            "net_margin": 5.0,
            "profit_growth": -5.0,
            "ocf_to_net_profit": 0.3,
            "pe_ttm": 50.0,
            "pb": 5.0,
            "turnover": 0.5,
            "revenue_growth": -5.0,
        },
    }
    results = engine.score_batch(stocks, metrics_map)
    assert results[0].symbol == "A"
    assert results[0].total_score > results[1].total_score
    assert results[0].quality_score > results[1].quality_score


def test_stability_score_checks_growth_direction():
    engine = ScoringEngine()
    metrics = {
        "revenue_growth": 10.0,
        "profit_growth": 15.0,
        "profit_deducted_growth": 12.0,
        "ocf_to_net_profit": 1.0,
    }
    score, details = engine._stability_score(metrics)
    assert score == 1.0
    assert details["revenue_growing"] is True


def test_value_score_pe_zero_gets_zero():
    engine = ScoringEngine()
    metrics = {"pe_ttm": -5.0, "pb": 2.0}
    benchmark = {"pe_ttm": [5.0, 10.0, 15.0], "pb": [1.0, 2.0, 3.0]}
    score, details = engine._value_score(metrics, benchmark)
    assert score >= 0.0
    assert details.get("pe_score") == 0.0
