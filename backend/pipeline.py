"""主流程：数据拉取 -> 过滤 -> 评分 -> 存档。"""
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.data.factory import get_provider
from backend.database.models import (
    Stock, FinancialMetric, StockScore, DailySnapshot, UpdateLog,
)
from backend.filters.engine import FilterEngine
from backend.scoring.engine import ScoringEngine
from backend.quality.engine import DataQualityEngine


def normalize_symbol(symbol: str) -> str:
    """统一代码格式。"""
    return str(symbol).strip().zfill(6)


class ScreenerPipeline:
    """选股流水线。"""

    def __init__(self, provider_name: str = "mock"):
        self.provider = get_provider(provider_name)
        self.filter_engine = FilterEngine()
        self.scoring_engine = ScoringEngine()
        self.now = datetime.utcnow()

    def _persist_metrics(self, db: Session, metrics_map: Dict[str, Dict[str, Any]]):
        """把合并后的指标持久化到 FinancialMetric 表。"""
        for sym, item in metrics_map.items():
            existing = db.query(FinancialMetric).filter(FinancialMetric.symbol == sym).first()
            if existing:
                for k, v in item.items():
                    if hasattr(existing, k) and k != "id":
                        setattr(existing, k, v)
            else:
                # 过滤掉模型中没有的字段
                valid_keys = {c.name for c in FinancialMetric.__table__.columns}
                data = {k: v for k, v in item.items() if k in valid_keys}
                db.add(FinancialMetric(**data))
        db.commit()

    def run(self, db: Session, max_stocks: int = 500) -> Dict[str, Any]:
        """运行完整流程。"""
        start_time = datetime.utcnow()
        log = UpdateLog(status="running", message="开始数据更新", provider=self.provider.name)
        db.add(log)
        db.commit()

        try:
            # 1. 拉取股票列表
            print("[1/5] 拉取股票列表...")
            stocks = self.provider.get_stock_list()
            if max_stocks:
                stocks = stocks[:max_stocks]

            # 写入或更新 stocks 表
            for s in stocks:
                existing = db.query(Stock).filter(Stock.symbol == s["symbol"]).first()
                if existing:
                    existing.name = s["name"]
                    existing.industry = s["industry"]
                    existing.sector = s["sector"]
                    existing.market = s["market"]
                else:
                    db.add(Stock(**s))
            db.commit()

            symbols = [s["symbol"] for s in stocks]

            # 2. 拉取财务指标
            print("[2/5] 拉取财务指标...")
            financial_data = self.provider.get_financial_metrics(symbols)
            metrics_map = {}
            for item in financial_data:
                sym = normalize_symbol(item["symbol"])
                item["symbol"] = sym
                metrics_map[sym] = item

            # 3. 拉取行情（估值、动量）并合并
            print("[3/5] 拉取行情数据...")
            price_data = self.provider.get_daily_prices(symbols)
            for item in price_data:
                sym = normalize_symbol(item["symbol"])
                if sym not in metrics_map:
                    # 如果财务数据缺失，用行情数据兜底
                    metrics_map[sym] = {"symbol": sym}
                metrics_map[sym].update(item)

            # 4. 数据质量评估
            print("[4/5] 数据质量评估...")
            quality_reports = DataQualityEngine.evaluate_all(
                metrics_map, source=self.provider.name, freshness=self.now
            )
            metrics_map = DataQualityEngine.enrich_metrics_with_quality(metrics_map, quality_reports)
            avg_completeness = DataQualityEngine.average_completeness(quality_reports)

            # 持久化所有指标（包括行情数据）
            self._persist_metrics(db, metrics_map)

            # 5. 过滤
            print("[5/5] 运行过滤...")
            filter_results = self.filter_engine.evaluate_batch(stocks, metrics_map)
            passed_symbols = {r.symbol for r in filter_results if r.passed}
            filter_reasons_map = {r.symbol: r.reasons for r in filter_results}

            # 6. 评分
            print("[6/6] 运行评分...")
            passed_stocks = [s for s in stocks if s["symbol"] in passed_symbols]
            score_results = self.scoring_engine.score_batch(passed_stocks, metrics_map)

            # 写入评分结果
            for sr in score_results:
                db.add(StockScore(
                    symbol=sr.symbol,
                    score_date=self.now,
                    quality_score=sr.quality_score,
                    value_score=sr.value_score,
                    momentum_score=sr.momentum_score,
                    total_score=sr.total_score,
                    passed_filters=True,
                    filter_reasons="[]",
                ))

            for r in filter_results:
                if not r.passed:
                    db.add(StockScore(
                        symbol=r.symbol,
                        score_date=self.now,
                        quality_score=0.0,
                        value_score=0.0,
                        momentum_score=0.0,
                        total_score=0.0,
                        passed_filters=False,
                        filter_reasons=str(r.reasons),
                    ))
            db.commit()

            # 7. 生成每日快照
            print("[存档] 保存今日快照...")
            snapshot_date = self.now.strftime("%Y-%m-%d")
            db.query(DailySnapshot).filter(DailySnapshot.snapshot_date == snapshot_date).delete()
            db.commit()

            for sr in score_results:
                stock = next((s for s in stocks if s["symbol"] == sr.symbol), {})
                metrics = metrics_map.get(sr.symbol, {})
                db.add(DailySnapshot(
                    snapshot_date=snapshot_date,
                    symbol=sr.symbol,
                    name=stock.get("name", ""),
                    industry=stock.get("industry", ""),
                    total_score=sr.total_score,
                    quality_score=sr.quality_score,
                    value_score=sr.value_score,
                    momentum_score=sr.momentum_score,
                    pe_ttm=metrics.get("pe_ttm"),
                    pb=metrics.get("pb"),
                    roe=metrics.get("roe"),
                    debt_to_asset=metrics.get("debt_to_asset"),
                    dividend_yield=metrics.get("dividend_yield"),
                    data_json=str(metrics),
                ))
            db.commit()

            # 更新日志
            log.status = "success"
            log.message = f"数据更新成功，平均完整度 {avg_completeness:.1%}"
            log.stocks_count = len(stocks)
            log.completeness_avg = avg_completeness
            db.commit()

            return {
                "status": "success",
                "stocks_count": len(stocks),
                "passed_count": len(passed_stocks),
                "completeness_avg": avg_completeness,
                "top_scores": [
                    {
                        "symbol": sr.symbol,
                        "name": next((s["name"] for s in stocks if s["symbol"] == sr.symbol), ""),
                        "total_score": sr.total_score,
                    }
                    for sr in score_results[:10]
                ],
            }

        except Exception as e:
            log.status = "failed"
            log.message = str(e)
            db.commit()
            raise
