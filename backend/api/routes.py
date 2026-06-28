"""FastAPI 路由。"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, PlainTextResponse
from sqlalchemy.orm import Session

from backend.database.connection import get_db
from backend.database.models import Stock, FinancialMetric, StockScore, DailySnapshot, UpdateLog
from backend.advisor.service import AIAdvisor
from backend.pipeline import ScreenerPipeline

router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


@router.post("/run")
def run_pipeline(db: Session = Depends(get_db)):
    """手动触发选股流程。"""
    pipeline = ScreenerPipeline()
    result = pipeline.run(db, max_stocks=500)
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
        return {"date": None, "items": []}

    date = latest.snapshot_date
    query = db.query(DailySnapshot).filter(DailySnapshot.snapshot_date == date)

    if min_score is not None:
        query = query.filter(DailySnapshot.total_score >= min_score)
    if industry:
        query = query.filter(DailySnapshot.industry == industry)

    items = query.order_by(DailySnapshot.total_score.desc()).all()

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

    return {
        "symbol": stock.symbol,
        "name": stock.name,
        "industry": stock.industry,
        "market": stock.market,
        "metrics": {
            "roe": metrics.roe if metrics else None,
            "roa": metrics.roa if metrics else None,
            "gross_margin": metrics.gross_margin if metrics else None,
            "net_margin": metrics.net_margin if metrics else None,
            "revenue_growth": metrics.revenue_growth if metrics else None,
            "profit_growth": metrics.profit_growth if metrics else None,
            "debt_to_asset": metrics.debt_to_asset if metrics else None,
            "current_ratio": metrics.current_ratio if metrics else None,
            "pe_ttm": metrics.pe_ttm if metrics else None,
            "pb": metrics.pb if metrics else None,
            "dividend_yield": metrics.dividend_yield if metrics else None,
            "audit_opinion": metrics.audit_opinion if metrics else None,
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

    # TradingView watchlist CSV 格式：第一列是 symbol，需要加交易所前缀
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
        }
        for log in logs
    ]


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
