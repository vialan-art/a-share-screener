"""FastAPI 路由。"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import Stock, FinancialMetric, StockScore, DailySnapshot, UpdateLog, AppConfig
from backend.advisor.service import AIAdvisor
from backend.pipeline import ScreenerPipeline
from backend.core.config import Settings, get_settings

router = APIRouter()


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
def run_pipeline(db: Session = Depends(get_db)):
    """手动触发选股流程。默认使用 mock 数据源保证稳定性，
    生产环境可通过环境变量或设置页面切换为 akshare / us。"""
    from backend.config import get_provider_name, get_config
    provider_name = get_provider_name()
    max_stocks = int(get_config("max_stocks", "500"))
    pipeline = ScreenerPipeline(provider_name=provider_name)
    result = pipeline.run(db, max_stocks=max_stocks)
    return result


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
                "momentum_score": i.momentum_score,
                "pe_ttm": i.pe_ttm,
                "pb": i.pb,
                "roe": i.roe,
                "debt_to_asset": i.debt_to_asset,
                "dividend_yield": i.dividend_yield,
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
                "momentum_score": i.momentum_score,
                "pe_ttm": i.pe_ttm,
                "pb": i.pb,
                "roe": i.roe,
                "debt_to_asset": i.debt_to_asset,
                "dividend_yield": i.dividend_yield,
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
            "issues": [],
        },
        "score": {
            "total": latest_score.total_score if latest_score else None,
            "quality": latest_score.quality_score if latest_score else None,
            "value": latest_score.value_score if latest_score else None,
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
