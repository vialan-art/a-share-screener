"""主流程：数据拉取 -> 过滤 -> 评分 -> 存档（生产级优化）。

优化点：
1. 分阶段拉取数据，单点失败不导致整个流程崩溃
2. 详细日志和运行时间统计
3. 数据质量报告持久化到 UpdateLog
4. 支持全市场 5000+ 只股票
"""
from datetime import datetime
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.data.factory import get_provider
from backend.database.models import (
    Stock, FinancialMetric, StockScore, DailySnapshot, UpdateLog, Portfolio,
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
        valid_keys = {c.name for c in FinancialMetric.__table__.columns}
        for sym, item in metrics_map.items():
            existing = db.query(FinancialMetric).filter(FinancialMetric.symbol == sym).first()
            data = {k: v for k, v in item.items() if k in valid_keys and k != "id"}
            if existing:
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                db.add(FinancialMetric(**data))
        db.commit()

    def run(self, db: Session, max_stocks: int = 5000, progress_callback=None) -> Dict[str, Any]:
        """运行完整流程。"""
        def _progress(msg: str):
            if progress_callback:
                progress_callback(msg)

        start_time = datetime.utcnow()
        log = UpdateLog(status="running", message="开始数据更新", provider=self.provider.name)
        db.add(log)
        db.commit()

        stats = {
            "stage_times": {},
            "errors": [],
        }

        try:
            # 1. 拉取股票列表
            stage_start = datetime.utcnow()
            _progress("[1/5] 拉取股票列表...")
            print("[1/5] 拉取股票列表...")
            try:
                stocks = self.provider.get_stock_list()
            except Exception as e:
                error_msg = f"拉取股票列表失败: {e}"
                print(error_msg)
                stats["errors"].append(error_msg)
                raise

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
            stats["stage_times"]["stock_list"] = (datetime.utcnow() - stage_start).total_seconds()
            _progress(f"[1/5] 完成，共 {len(stocks)} 只股票")
            print(f"[1/5] 完成，共 {len(stocks)} 只股票")

            symbols = [s["symbol"] for s in stocks]

            # 2. 拉取财务指标
            stage_start = datetime.utcnow()
            _progress("[2/5] 拉取财务指标...")
            print("[2/5] 拉取财务指标...")
            try:
                financial_data = self.provider.get_financial_metrics(symbols)
            except Exception as e:
                error_msg = f"拉取财务指标失败: {e}"
                print(error_msg)
                stats["errors"].append(error_msg)
                financial_data = []

            metrics_map = {}
            for item in financial_data:
                sym = normalize_symbol(item["symbol"])
                item["symbol"] = sym
                metrics_map[sym] = item
            stats["stage_times"]["financial_metrics"] = (datetime.utcnow() - stage_start).total_seconds()
            _progress(f"[2/5] 完成，财务数据覆盖 {len(metrics_map)} 只股票")
            print(f"[2/5] 完成，财务数据覆盖 {len(metrics_map)} 只股票")

            # 3. 拉取行情（估值、动量）并合并
            stage_start = datetime.utcnow()
            _progress("[3/5] 拉取行情数据...")
            print("[3/5] 拉取行情数据...")
            try:
                price_data = self.provider.get_daily_prices(symbols)
            except Exception as e:
                error_msg = f"拉取行情失败: {e}"
                print(error_msg)
                stats["errors"].append(error_msg)
                price_data = []

            for item in price_data:
                sym = normalize_symbol(item["symbol"])
                if sym not in metrics_map:
                    metrics_map[sym] = {"symbol": sym}
                metrics_map[sym].update(item)
            stats["stage_times"]["daily_prices"] = (datetime.utcnow() - stage_start).total_seconds()
            _progress(f"[3/5] 完成，行情数据覆盖 {len(price_data)} 只股票")
            print(f"[3/5] 完成，行情数据覆盖 {len(price_data)} 只股票")

            # 4. 数据质量评估
            stage_start = datetime.utcnow()
            _progress("[4/5] 数据质量评估...")
            print("[4/5] 数据质量评估...")
            quality_reports = DataQualityEngine.evaluate_all(
                metrics_map, source=self.provider.name, freshness=self.now
            )
            metrics_map = DataQualityEngine.enrich_metrics_with_quality(metrics_map, quality_reports)
            avg_completeness = DataQualityEngine.average_completeness(quality_reports)
            issue_summary = DataQualityEngine.issue_summary(quality_reports)
            stats["stage_times"]["quality"] = (datetime.utcnow() - stage_start).total_seconds()
            _progress(f"[4/5] 完成，平均完整度 {avg_completeness:.1%}")
            print(f"[4/5] 完成，平均完整度 {avg_completeness:.1%}")

            # 持久化所有指标（包括行情数据）
            self._persist_metrics(db, metrics_map)

            # 5. 过滤
            stage_start = datetime.utcnow()
            _progress("[5/5] 运行过滤...")
            print("[5/5] 运行过滤...")
            # 用业绩快报中的行业分类覆盖静态映射，提高过滤规则准确性
            for s in stocks:
                m = metrics_map.get(s["symbol"], {})
                if m.get("industry"):
                    s["industry"] = m["industry"]
            filter_results = self.filter_engine.evaluate_batch(stocks, metrics_map)
            passed_symbols = {r.symbol for r in filter_results if r.passed}
            filter_reasons_map = {r.symbol: r.reasons for r in filter_results}
            stats["stage_times"]["filter"] = (datetime.utcnow() - stage_start).total_seconds()
            _progress(f"[5/5] 完成，{len(passed_symbols)}/{len(stocks)} 只通过过滤")
            print(f"[5/5] 完成，{len(passed_symbols)}/{len(stocks)} 只通过过滤")

            # 6. 评分
            stage_start = datetime.utcnow()
            _progress("[6/6] 运行评分...")
            print("[6/6] 运行评分...")
            passed_stocks = [s for s in stocks if s["symbol"] in passed_symbols]
            score_results = self.scoring_engine.score_batch(passed_stocks, metrics_map)
            stats["stage_times"]["scoring"] = (datetime.utcnow() - stage_start).total_seconds()
            _progress(f"[6/6] 完成，评分 {len(score_results)} 只股票")
            print(f"[6/6] 完成，评分 {len(score_results)} 只股票")

            # 写入评分结果
            for sr in score_results:
                db.add(StockScore(
                    symbol=sr.symbol,
                    score_date=self.now,
                    quality_score=sr.quality_score,
                    value_score=sr.value_score,
                    momentum_score=sr.momentum_score,
                    stability_score=sr.stability_score,
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
                        stability_score=0.0,
                        total_score=0.0,
                        passed_filters=False,
                        filter_reasons=str(r.reasons),
                    ))
            db.commit()

            # 7. 生成每日快照
            stage_start = datetime.utcnow()
            _progress("[存档] 保存今日快照...")
            print("[存档] 保存今日快照...")
            snapshot_date = self.now.strftime("%Y-%m-%d")
            db.query(DailySnapshot).filter(DailySnapshot.snapshot_date == snapshot_date).delete()
            db.commit()

            for sr in score_results:
                stock = next((s for s in stocks if s["symbol"] == sr.symbol), {})
                metrics = metrics_map.get(sr.symbol, {})
                enriched_metrics = dict(metrics)
                # 移除不可 JSON 序列化的对象
                enriched_metrics.pop("data_freshness", None)
                enriched_metrics["_score_details"] = sr.details
                enriched_metrics["_filter_reasons"] = []
                db.add(DailySnapshot(
                    snapshot_date=snapshot_date,
                    symbol=sr.symbol,
                    name=stock.get("name", ""),
                    industry=stock.get("industry", ""),
                    total_score=sr.total_score,
                    quality_score=sr.quality_score,
                    value_score=sr.value_score,
                    momentum_score=sr.momentum_score,
                    stability_score=sr.stability_score,
                    pe_ttm=metrics.get("pe_ttm"),
                    pb=metrics.get("pb"),
                    roe=metrics.get("roe"),
                    debt_to_asset=metrics.get("debt_to_asset"),
                    dividend_yield=metrics.get("dividend_yield"),
                    data_json=json.dumps(enriched_metrics, ensure_ascii=False, default=str),
                ))
            db.commit()
            stats["stage_times"]["snapshot"] = (datetime.utcnow() - stage_start).total_seconds()

            # 8. 保存实盘推荐组合
            stage_start = datetime.utcnow()
            _progress("[实盘] 保存推荐组合...")
            print("[实盘] 保存推荐组合...")
            self._save_portfolio(db, snapshot_date, score_results, stocks)
            stats["stage_times"]["portfolio"] = (datetime.utcnow() - stage_start).total_seconds()

            total_time = (datetime.utcnow() - start_time).total_seconds()
            stats["stage_times"]["total"] = total_time

            # 更新日志
            log.status = "success"
            log.message = f"数据更新成功，平均完整度 {avg_completeness:.1%}"
            log.stocks_count = len(stocks)
            log.completeness_avg = avg_completeness
            log.provider = self.provider.name
            db.commit()

            return {
                "status": "success",
                "stocks_count": len(stocks),
                "passed_count": len(passed_stocks),
                "completeness_avg": avg_completeness,
                "issue_summary": issue_summary,
                "stage_times": stats["stage_times"],
                "errors": stats["errors"],
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

    def _save_portfolio(self, db: Session, snapshot_date: str, score_results, stocks: List[Dict[str, Any]], top_n: int = 20):
        """保存当日 Top N 推荐组合为实盘跟踪组合。"""
        # 只保留前 top_n
        top = score_results[:top_n]
        if not top:
            return

        db.query(Portfolio).filter(Portfolio.portfolio_date == snapshot_date).delete()
        db.commit()

        weight = round(1.0 / len(top), 6)
        for sr in top:
            stock = next((s for s in stocks if s["symbol"] == sr.symbol), {})
            db.add(Portfolio(
                portfolio_date=snapshot_date,
                symbol=sr.symbol,
                name=stock.get("name", ""),
                industry=stock.get("industry", ""),
                total_score=sr.total_score,
                weight=weight,
                data_json=json.dumps({"score_details": sr.details}, ensure_ascii=False),
            ))
        db.commit()
