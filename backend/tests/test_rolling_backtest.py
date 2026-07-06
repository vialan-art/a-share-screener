"""滚动回测引擎最小单元测试（使用内存 SQLite + mock PriceService）。"""
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, DailySnapshot, StockPrice
from backend.backtest.rolling import RollingBacktest


class MockPriceService:
    """Mock PriceService：价格按 symbol 编码规则生成，无需外部网络。"""

    def __init__(self, db):
        self.db = db

    def get_adj_close(self, symbol, start_date, end_date):
        import pandas as pd
        # 用 symbol 的 ASCII 和生成确定性涨幅：0 ~ 5% / 天
        seed = sum(ord(c) for c in symbol)
        dates = []
        close = 10.0
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")
        current = start
        while current <= end:
            dates.append({
                "trade_date": current.strftime("%Y%m%d"),
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "adj_open": close,
                "adj_close": close,
                "vol": 1000,
            })
            # 每天固定小涨幅，不同 symbol 幅度不同
            close *= 1 + ((seed % 50) + 1) / 1000
            current += __import__("datetime").timedelta(days=1)
        return pd.DataFrame(dates)

    def get_index_return(self, index_code, start_date, end_date):
        return 0.5  # 基准每期固定 0.5%


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _add_snapshot(db, date, symbol, score):
    db.add(DailySnapshot(
        snapshot_date=date,
        symbol=symbol,
        name=symbol,
        industry="test",
        total_score=score,
        quality_score=0.5,
        value_score=0.5,
        momentum_score=0.5,
        stability_score=0.5,
    ))


def test_rolling_backtest_daily_frequency(db):
    for i, date in enumerate(["2026-06-29", "2026-06-30", "2026-07-01", "2026-07-02"]):
        for sym in ["000001", "000002", "000003", "000004", "000005"]:
            _add_snapshot(db, date, sym, 0.8 - i * 0.01)
    db.commit()

    engine = RollingBacktest(db, seed=42)
    # 注入 mock price service
    engine.price_service = MockPriceService(db)
    result = engine.run(top_n=3, frequency="daily")

    assert "error" not in result
    assert result["frequency"] == "daily"
    assert result["periods"] == 3
    assert result["strategy"]["total_return"] > 0
    assert result["benchmark"]["total_return"] is not None
    assert len(result["records"]) == 3


def test_rolling_backtest_falls_back_to_daily(db):
    for i, date in enumerate(["2026-07-01", "2026-07-02", "2026-07-03"]):
        for sym in ["000001", "000002"]:
            _add_snapshot(db, date, sym, 0.8 - i * 0.01)
    db.commit()

    engine = RollingBacktest(db, seed=42)
    engine.price_service = MockPriceService(db)
    result = engine.run(top_n=2, frequency="auto")

    assert "error" not in result
    assert result["frequency"] == "daily"
    assert result["periods"] == 2


def test_rolling_backtest_not_enough_snapshots(db):
    _add_snapshot(db, "2026-06-29", "000001", 0.8)
    db.commit()

    engine = RollingBacktest(db, seed=42)
    engine.price_service = MockPriceService(db)
    result = engine.run(top_n=2)

    assert "error" in result
