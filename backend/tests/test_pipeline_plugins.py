"""插件 + pipeline 集成的最小测试。"""
import json
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, Stock, FinancialMetric, DailySnapshot
from backend.scoring.engine import ScoringEngine
from backend.plugins.adapter import PluginAdapter
from backend.plugins.data_service import PluginDataService


class MockPriceService:
    """生成 mock OHLCV，无需网络。"""

    def __init__(self, db):
        self.db = db

    def get_adj_close(self, symbol, start_date, end_date):
        import pandas as pd
        dates = []
        close = 10.0
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        current = start
        while current <= end:
            dates.append({
                "trade_date": current.strftime("%Y%m%d"),
                "open": close,
                "high": close * 1.02,
                "low": close * 0.98,
                "close": close,
                "adj_open": close,
                "adj_close": close,
                "volume": 1000,
            })
            close *= 1.001
            current += __import__("datetime").timedelta(days=1)
        return pd.DataFrame(dates)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_plugin_enrich_and_score(db):
    """验证插件信号能被 enrich 到 metrics，并影响评分。"""
    # 准备股票
    db.add(Stock(symbol="000001", name="平安银行", industry="银行"))
    db.commit()

    stocks = [{"symbol": "000001", "name": "平安银行", "industry": "银行"}]
    metrics_map = {
        "000001": {
            "symbol": "000001",
            "roe": 12.0,
            "pe_ttm": 8.0,
            "pb": 0.9,
            "turnover": 1.5,
            "profit_growth": 10.0,
            "revenue_growth": 8.0,
        }
    }

    # 用 mock price service 拉 K 线
    plugin_data = PluginDataService(db)
    plugin_data.price_service = MockPriceService(db)
    ohlcv_map = plugin_data.fetch_batch(["000001"], days=300)
    assert "000001" in ohlcv_map
    assert len(ohlcv_map["000001"]) > 250

    # enrich
    adapter = PluginAdapter()
    enriched = adapter.enrich_batch(stocks, metrics_map, ohlcv_map)
    m = enriched["000001"]
    assert "_plugin_signals" in m
    assert any(s["signal_type"] == "indicator" for s in m["_plugin_signals"].values())

    # 评分
    engine = ScoringEngine()
    results = engine.score_batch(stocks, enriched)
    assert len(results) == 1
    assert results[0].total_score > 0
    assert "technical" in results[0].details
    technical_details = results[0].details["technical"]
    assert "indicator" in technical_details or "strategy" in technical_details
    assert any(v >= 0 for v in technical_details.values() if isinstance(v, (int, float)))


def test_daily_snapshot_with_plugin_signals(db):
    """模拟把 enrich 后的 metrics 写入 DailySnapshot。"""
    db.add(Stock(symbol="000001", name="平安银行", industry="银行"))
    db.commit()

    stocks = [{"symbol": "000001", "name": "平安银行", "industry": "银行"}]
    metrics_map = {"000001": {"symbol": "000001", "roe": 12.0}}

    plugin_data = PluginDataService(db)
    plugin_data.price_service = MockPriceService(db)
    ohlcv_map = plugin_data.fetch_batch(["000001"], days=60)

    adapter = PluginAdapter()
    enriched = adapter.enrich_batch(stocks, metrics_map, ohlcv_map)
    metrics = enriched["000001"]

    data_json = json.dumps(metrics, ensure_ascii=False, default=str)
    db.add(DailySnapshot(
        snapshot_date="2026-07-06",
        symbol="000001",
        name="平安银行",
        industry="银行",
        total_score=0.75,
        data_json=data_json,
    ))
    db.commit()

    snap = db.query(DailySnapshot).filter(DailySnapshot.symbol == "000001").first()
    parsed = json.loads(snap.data_json)
    assert "_plugin_signals" in parsed
