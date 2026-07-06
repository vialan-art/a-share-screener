"""FastAPI 路由。"""
import ast
import json
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session
import threading
import uuid

from backend.database.connection import get_db, SessionLocal
from backend.database.models import Stock, FinancialMetric, StockScore, DailySnapshot, UpdateLog, AppConfig, Portfolio, PortfolioNav
from backend.advisor.service import AIAdvisor
from backend.pipeline import ScreenerPipeline
from backend.core.config import Settings, get_settings

router = APIRouter()


def _extract_reasons(data_json: Optional[str]) -> List[str]:
    """从快照 data_json 中提取入选理由。"""
    if not data_json:
        return []
    try:
        data = json.loads(data_json)
        details = data.get("_score_details", {})
        reasons = []
        quality = details.get("quality", {})
        value = details.get("value", {})
        stability = details.get("stability", {})
        if quality.get("roe_score", 0) >= 0.7:
            reasons.append("ROE优秀")
        if quality.get("growth_score", 0) >= 0.7:
            reasons.append("增长强劲")
        if quality.get("ocf_ratio_score", 0) >= 0.7:
            reasons.append("现金流健康")
        if value.get("pe_score", 0) >= 0.7:
            reasons.append("PE低估")
        if value.get("pb_score", 0) >= 0.7:
            reasons.append("PB低估")
        if stability.get("ocf_strong"):
            reasons.append("盈利质量稳")
        if stability.get("revenue_growing") and stability.get("profit_growing"):
            reasons.append("增长一致")
        return reasons[:3]
    except Exception:
        return []


# ponytail: in-memory job store for single uvicorn worker. Switch to Redis if scaled.
_jobs: dict = {}
_jobs_lock = threading.Lock()


def _prune_jobs():
    cutoff = datetime.utcnow() - timedelta(hours=2)
    with _jobs_lock:
        stale = [jid for jid, j in _jobs.items() if j.get("created_at", datetime.utcnow()) < cutoff]
        for jid in stale:
            _jobs.pop(jid, None)


def _set_job(jid: str, **kwargs):
    with _jobs_lock:
        job = _jobs.setdefault(jid, {
            "id": jid,
            "status": "queued",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "progress": "排队中",
            "result": None,
            "error": None,
        })
        job.update(kwargs)
        job["updated_at"] = datetime.utcnow()


def _execute_pipeline(jid: str):
    """在后台线程中执行选股流程。"""
    db = SessionLocal()
    try:
        _set_job(jid, status="running", progress="初始化数据源...")
        from backend.config import get_provider_name, get_config
        provider_name = get_provider_name()
        max_stocks = int(get_config("max_stocks", "500"))

        pipeline = ScreenerPipeline(provider_name=provider_name)
        _set_job(jid, progress="开始拉取数据...")
        result = pipeline.run(db, max_stocks=max_stocks, progress_callback=lambda msg: _set_job(jid, progress=msg))
        _set_job(jid, status="success", progress="完成", result=result)
    except Exception as e:
        _set_job(jid, status="failed", progress="失败", error=str(e))
    finally:
        db.close()


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@router.get("/health")
def health_check():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@router.post("/run")
def run_pipeline():
    """手动触发选股流程，立即返回 job_id，后台异步执行。
    客户端通过 /run/status/{job_id} 轮询结果。"""
    _prune_jobs()
    jid = str(uuid.uuid4())
    _set_job(jid, status="queued", progress="排队中")
    thread = threading.Thread(target=_execute_pipeline, args=(jid,), daemon=True)
    thread.start()
    return {"job_id": jid, "status": "queued", "check_url": f"/api/v1/run/status/{jid}"}


@router.get("/run/status/{job_id}")
def get_run_status(job_id: str):
    """查询选股任务状态。"""
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")
    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "result": job["result"],
        "error": job["error"],
        "created_at": job["created_at"].isoformat() if job.get("created_at") else None,
        "updated_at": job["updated_at"].isoformat() if job.get("updated_at") else None,
    }


@router.get("/stocks", response_model=List[dict])
def list_stocks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    stocks = db.query(Stock).offset(skip).limit(limit).all()
    return [
        {
            "symbol": s.symbol,
            "name": s.name,
            "industry": s.industry,
            "market": s.market,
        }
        for s in stocks
    ]


@router.get("/snapshot/latest")
def get_latest_snapshot(
    min_score: Optional[float] = None,
    industry: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取最新快照，支持筛选。"""
    latest = db.query(DailySnapshot).order_by(DailySnapshot.snapshot_date.desc()).first()
    if not latest:
        return {"date": None, "items": [], "meta": {}}

    date = latest.snapshot_date
    query = db.query(DailySnapshot).filter(DailySnapshot.snapshot_date == date)

    if min_score is not None:
        query = query.filter(DailySnapshot.total_score >= min_score)
    if industry:
        query = query.filter(DailySnapshot.industry == industry)

    items = query.order_by(DailySnapshot.total_score.desc()).all()

    # 计算快照统计信息
    scores = [i.total_score for i in items if i.total_score is not None]
    industries = {}
    for i in items:
        industries[i.industry] = industries.get(i.industry, 0) + 1

    return {
        "date": date,
        "count": len(items),
        "meta": {
            "avg_score": round(sum(scores) / len(scores), 4) if scores else None,
            "max_score": round(max(scores), 4) if scores else None,
            "min_score": round(min(scores), 4) if scores else None,
            "industry_distribution": dict(sorted(industries.items(), key=lambda x: x[1], reverse=True)[:15]),
        },
        "items": [
            {
                "symbol": i.symbol,
                "name": i.name,
                "industry": i.industry,
                "total_score": i.total_score,
                "quality_score": i.quality_score,
                "value_score": i.value_score,
                "stability_score": i.stability_score,
                "momentum_score": i.momentum_score,
                "pe_ttm": i.pe_ttm,
                "pb": i.pb,
                "roe": i.roe,
                "debt_to_asset": i.debt_to_asset,
                "dividend_yield": i.dividend_yield,
                "_reasons": _extract_reasons(i.data_json),
            }
            for i in items
        ],
    }


@router.get("/snapshot/dates")
def get_snapshot_dates(db: Session = Depends(get_db)):
    """获取所有有快照的日期。"""
    dates = db.query(DailySnapshot.snapshot_date).distinct().order_by(DailySnapshot.snapshot_date.desc()).all()
    return [d[0] for d in dates]


@router.get("/snapshot/{date}")
def get_snapshot_by_date(date: str, db: Session = Depends(get_db)):
    items = db.query(DailySnapshot).filter(DailySnapshot.snapshot_date == date).order_by(DailySnapshot.total_score.desc()).all()
    return {
        "date": date,
        "count": len(items),
        "items": [
            {
                "symbol": i.symbol,
                "name": i.name,
                "industry": i.industry,
                "total_score": i.total_score,
                "quality_score": i.quality_score,
                "value_score": i.value_score,
                "stability_score": i.stability_score,
                "momentum_score": i.momentum_score,
                "pe_ttm": i.pe_ttm,
                "pb": i.pb,
                "roe": i.roe,
                "debt_to_asset": i.debt_to_asset,
                "dividend_yield": i.dividend_yield,
                "_reasons": _extract_reasons(i.data_json),
            }
            for i in items
        ],
    }


@router.get("/stock/{symbol}")
def get_stock_detail(symbol: str, db: Session = Depends(get_db)):
    """获取单只股票详情。"""
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="股票不存在")

    metrics = db.query(FinancialMetric).filter(FinancialMetric.symbol == symbol).first()
    latest_score = db.query(StockScore).filter(StockScore.symbol == symbol).order_by(StockScore.score_date.desc()).first()

    def m(field):
        return getattr(metrics, field, None) if metrics else None

    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "industry": stock.industry,
        "market": stock.market,
        "metrics": {
            "roe": m("roe"),
            "roa": m("roa"),
            "gross_margin": m("gross_margin"),
            "net_margin": m("net_margin"),
            "revenue": m("revenue"),
            "revenue_growth": m("revenue_growth"),
            "net_profit": m("net_profit"),
            "profit_growth": m("profit_growth"),
            "net_profit_deducted": m("net_profit_deducted"),
            "profit_deducted_growth": m("profit_deducted_growth"),
            "debt_to_asset": m("debt_to_asset"),
            "interest_bearing_debt_ratio": m("interest_bearing_debt_ratio"),
            "current_ratio": m("current_ratio"),
            "quick_ratio": m("quick_ratio"),
            "total_assets": m("total_assets"),
            "total_equity": m("total_equity"),
            "operating_cash_flow": m("operating_cash_flow"),
            "operating_cash_flow_growth": m("operating_cash_flow_growth"),
            "capital_expenditure": m("capital_expenditure"),
            "free_cash_flow": m("free_cash_flow"),
            "ocf_to_net_profit": m("ocf_to_net_profit"),
            "latest_price": m("latest_price"),
            "change_pct": m("change_pct"),
            "turnover": m("turnover"),
            "pe_ttm": m("pe_ttm"),
            "pb": m("pb"),
            "ps_ttm": m("ps_ttm"),
            "dividend_yield": m("dividend_yield"),
            "audit_opinion": m("audit_opinion"),
        },
        "data_quality": {
            "source": m("data_source") or "unknown",
            "freshness": m("data_freshness").isoformat() if m("data_freshness") else None,
            "completeness_score": m("completeness_score"),
            "data_source_note": m("data_source_note") or "",
            "issues": [],
        },
        "score": {
            "total": latest_score.total_score if latest_score else None,
            "quality": latest_score.quality_score if latest_score else None,
            "value": latest_score.value_score if latest_score else None,
            "stability": latest_score.stability_score if latest_score else None,
            "momentum": latest_score.momentum_score if latest_score else None,
            "passed_filters": latest_score.passed_filters if latest_score else None,
            "filter_reasons": latest_score.filter_reasons if latest_score else None,
        },
    }


@router.get("/export/watchlist")
def export_watchlist(db: Session = Depends(get_db)):
    """导出 TradingView watchlist CSV。"""
    latest = db.query(DailySnapshot).order_by(DailySnapshot.snapshot_date.desc()).first()
    if not latest:
        return PlainTextResponse("没有数据", status_code=404)

    date = latest.snapshot_date
    items = db.query(DailySnapshot).filter(DailySnapshot.snapshot_date == date).order_by(DailySnapshot.total_score.desc()).all()

    lines = ["symbol"]
    for i in items:
        prefix = "SSE:" if i.symbol.startswith("6") else "SZSE:"
        lines.append(f"{prefix}{i.symbol}")

    content = "\n".join(lines)
    filename = f"watchlist_{date}.csv"

    return PlainTextResponse(
        content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/logs")
def get_logs(limit: int = 20, db: Session = Depends(get_db)):
    logs = db.query(UpdateLog).order_by(UpdateLog.update_time.desc()).limit(limit).all()
    return [
        {
            "time": log.update_time.isoformat(),
            "status": log.status,
            "message": log.message,
            "stocks_count": log.stocks_count,
            "provider": log.provider,
            "completeness_avg": log.completeness_avg,
        }
        for log in logs
    ]


@router.get("/quality/detail")
def get_quality_detail(db: Session = Depends(get_db)):
    """获取详细的数据质量监控信息，用于 Dashboard 看板。"""
    from sqlalchemy import func
    from backend.database.models import FinancialMetric

    total = db.query(func.count(FinancialMetric.id)).scalar() or 0
    if total == 0:
        return {
            "total": 0,
            "with_price": 0,
            "with_profit": 0,
            "with_debt": 0,
            "with_cashflow": 0,
            "field_coverage": {},
            "recent_logs": [],
        }

    def ratio(q):
        return round((db.query(func.count(FinancialMetric.id)).filter(q).scalar() or 0) / total, 4)

    field_coverage = {
        "latest_price": ratio(FinancialMetric.latest_price != None),
        "pe_ttm": ratio(FinancialMetric.pe_ttm != None),
        "pb": ratio(FinancialMetric.pb != None),
        "roe": ratio(FinancialMetric.roe != None),
        "revenue": ratio(FinancialMetric.revenue != None),
        "net_profit": ratio(FinancialMetric.net_profit != None),
        "profit_growth": ratio(FinancialMetric.profit_growth != None),
        "debt_to_asset": ratio(FinancialMetric.debt_to_asset != None),
        "operating_cash_flow": ratio(FinancialMetric.operating_cash_flow != None),
        "free_cash_flow": ratio(FinancialMetric.free_cash_flow != None),
        "dividend_yield": ratio(FinancialMetric.dividend_yield != None),
    }

    recent_logs = db.query(UpdateLog).order_by(UpdateLog.update_time.desc()).limit(7).all()

    return {
        "total": total,
        "with_price": ratio(FinancialMetric.latest_price != None),
        "with_profit": ratio(FinancialMetric.net_profit != None),
        "with_debt": ratio(FinancialMetric.debt_to_asset != None),
        "with_cashflow": ratio(FinancialMetric.operating_cash_flow != None),
        "field_coverage": field_coverage,
        "estimation_note": (
            "debt_to_asset 缺省时使用 A 股市场默认值 45% 估算；"
            "cashflow / total_equity / total_assets 基于当日总市值与每股指标估算；"
            "ROA 使用净利润/总资产估算。"
        ),
        "recent_logs": [
            {
                "time": log.update_time.isoformat(),
                "status": log.status,
                "message": log.message,
                "stocks_count": log.stocks_count,
                "provider": log.provider,
                "completeness_avg": log.completeness_avg,
            }
            for log in recent_logs
        ],
    }


@router.get("/backtest/simple")
def run_simple_backtest(
    snapshot_date: Optional[str] = None,
    buy_date: Optional[str] = None,
    end_date: Optional[str] = None,
    top_n: int = 20,
    db: Session = Depends(get_db),
):
    """最小回测：取快照 Top N 等权重持有至今，对比沪深300。"""
    from backend.backtest.simple import SimpleBacktest

    engine = SimpleBacktest(db)
    if snapshot_date or buy_date:
        return engine.run(
            snapshot_date=snapshot_date,
            buy_date=buy_date,
            end_date=end_date,
            top_n=top_n,
        )
    return {"results": engine.run_multiple_horizons(top_n=top_n)}


@router.get("/backtest/rolling")
def run_rolling_backtest(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    top_n: int = 20,
    frequency: str = "auto",
    db: Session = Depends(get_db),
):
    """滚动回测：自动根据快照密度选择月度/周度调仓，等权持有 Top N，对比沪深300和随机选股。"""
    from backend.backtest.rolling import RollingBacktest

    engine = RollingBacktest(db)
    return engine.run(start_date=start_date, end_date=end_date, top_n=top_n, frequency=frequency)


@router.get("/portfolio/latest")
def get_latest_portfolio(top_n: int = 20, db: Session = Depends(get_db)):
    """获取最新实盘推荐组合。"""
    latest = db.query(Portfolio).order_by(Portfolio.portfolio_date.desc()).first()
    if not latest:
        return {"date": None, "items": []}
    items = (
        db.query(Portfolio)
        .filter(Portfolio.portfolio_date == latest.portfolio_date)
        .order_by(Portfolio.total_score.desc())
        .limit(top_n)
        .all()
    )
    return {
        "date": latest.portfolio_date,
        "items": [
            {
                "symbol": i.symbol,
                "name": i.name,
                "industry": i.industry,
                "total_score": i.total_score,
                "weight": i.weight,
            }
            for i in items
        ],
    }


@router.get("/portfolio/nav")
def get_portfolio_nav(limit: int = 252, db: Session = Depends(get_db)):
    """获取实盘组合历史净值。"""
    rows = (
        db.query(PortfolioNav)
        .order_by(PortfolioNav.nav_date.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "date": r.nav_date,
            "portfolio_return": r.portfolio_return,
            "benchmark_return": r.benchmark_return,
            "daily_return": r.daily_return,
            "benchmark_daily_return": r.benchmark_daily_return,
        }
        for r in rows
    ]


@router.get("/quality/summary")
def get_quality_summary(db: Session = Depends(get_db)):
    """获取最新数据质量摘要。"""
    from backend.quality.engine import DataQualityEngine
    from backend.database.models import FinancialMetric

    metrics = db.query(FinancialMetric).all()
    metrics_map = {}
    for m in metrics:
        d = {c.name: getattr(m, c.name) for c in FinancialMetric.__table__.columns}
        metrics_map[d["symbol"]] = d

    reports = DataQualityEngine.evaluate_all(
        metrics_map, source="db", freshness=datetime.utcnow()
    )
    return {
        "count": len(reports),
        "avg_completeness": DataQualityEngine.average_completeness(reports),
        "issue_summary": DataQualityEngine.issue_summary(reports),
    }


@router.post("/advisor/chat")
async def advisor_chat(request: dict):
    """AI 顾问非流式对话。"""
    messages = request.get("messages", [])
    advisor = AIAdvisor()
    return await advisor.chat(messages)


@router.post("/advisor/chat/stream")
async def advisor_chat_stream(request: dict):
    """AI 顾问流式对话。"""
    messages = request.get("messages", [])
    advisor = AIAdvisor()

    async def event_generator():
        async for chunk in advisor.chat_stream(messages):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# 默认配置项：前端设置页面展示的字段
DEFAULT_SETTINGS = {
    "ai_base_url": {"value": "", "description": "AI 助手 API Base URL（OpenAI 兼容）"},
    "ai_api_key": {"value": "", "description": "AI 助手 API Key"},
    "ai_model": {"value": "gpt-4o-mini", "description": "AI 助手模型名称"},
    "data_provider": {"value": "mock", "description": "默认数据源：mock / akshare / us"},
    "max_stocks": {"value": "500", "description": "单次选股最大股票数量"},
    "scheduler_time": {"value": "19:00", "description": "每日定时选股时间（HH:MM）"},
    "database_url": {"value": "", "description": "数据库 URL（留空使用默认 SQLite）"},
    "market_region": {"value": "cn", "description": "默认市场：cn（A股）/ us（美股）"},
    "tushare_token": {"value": "", "description": "Tushare Pro API Token（用于回测历史行情）"},
}


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    """获取所有应用配置。"""
    configs = db.query(AppConfig).all()
    result = {k: {"value": v["value"], "description": v["description"]} for k, v in DEFAULT_SETTINGS.items()}
    for c in configs:
        if c.key in result:
            result[c.key]["value"] = c.value
    return result


@router.post("/settings")
def update_settings(request: dict, db: Session = Depends(get_db)):
    """更新应用配置。"""
    for key, value in request.items():
        if key not in DEFAULT_SETTINGS:
            continue
        existing = db.query(AppConfig).filter(AppConfig.key == key).first()
        if existing:
            existing.value = str(value)
        else:
            db.add(AppConfig(
                key=key,
                value=str(value),
                description=DEFAULT_SETTINGS[key]["description"],
            ))
    db.commit()
    return {"status": "ok"}


@router.post("/settings/reset")
def reset_settings(db: Session = Depends(get_db)):
    """重置所有配置为默认值。"""
    db.query(AppConfig).delete()
    db.commit()
    return {"status": "ok"}
