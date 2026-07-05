"""每日定时任务调度器。

用 schedule 库每天 19:00 运行一次选股流程。
可以在服务器上长期运行这个脚本。
"""
import os
import schedule
import time
from datetime import datetime, timedelta

from backend.database.connection import SessionLocal
from backend.pipeline import ScreenerPipeline
from backend.config import get_provider_name, get_config
from backend.data.price_service import PriceService
from backend.database.models import Portfolio, PortfolioNav, StockPrice
from sqlalchemy import func


def _update_portfolio_nav(db):
    """更新实盘组合净值。取最新的 Portfolio 作为当前持仓，计算今日收益。"""
    latest_portfolio = db.query(Portfolio).order_by(Portfolio.portfolio_date.desc()).first()
    if not latest_portfolio:
        return

    portfolio_date = latest_portfolio.portfolio_date
    items = db.query(Portfolio).filter(Portfolio.portfolio_date == portfolio_date).all()
    if not items:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 如果已经有今日净值，跳过
    existing = db.query(PortfolioNav).filter(PortfolioNav.nav_date == today).first()
    if existing:
        return

    symbols = [i.symbol for i in items]
    daily_returns = []
    valid = 0
    for symbol in symbols:
        today_price = db.query(StockPrice).filter(
            StockPrice.symbol == symbol,
            StockPrice.trade_date <= today.replace("-", ""),
        ).order_by(StockPrice.trade_date.desc()).first()
        yesterday_price = db.query(StockPrice).filter(
            StockPrice.symbol == symbol,
            StockPrice.trade_date <= yesterday.replace("-", ""),
        ).order_by(StockPrice.trade_date.desc()).first()
        if today_price and yesterday_price and yesterday_price.adj_close > 0:
            daily_returns.append((today_price.adj_close - yesterday_price.adj_close) / yesterday_price.adj_close)
            valid += 1

    if valid == 0:
        return

    portfolio_daily = sum(daily_returns) / len(daily_returns)

    # 沪深300当日收益
    benchmark_today = db.query(StockPrice).filter(
        StockPrice.symbol == "000300.SH",
        StockPrice.trade_date <= today.replace("-", ""),
    ).order_by(StockPrice.trade_date.desc()).first()
    benchmark_yesterday = db.query(StockPrice).filter(
        StockPrice.symbol == "000300.SH",
        StockPrice.trade_date <= yesterday.replace("-", ""),
    ).order_by(StockPrice.trade_date.desc()).first()
    benchmark_daily = 0.0
    if benchmark_today and benchmark_yesterday and benchmark_yesterday.adj_close > 0:
        benchmark_daily = (benchmark_today.adj_close - benchmark_yesterday.adj_close) / benchmark_yesterday.adj_close

    # 累计收益：从组合成立日起
    first_nav = db.query(PortfolioNav).order_by(PortfolioNav.nav_date.asc()).first()
    portfolio_total = ((first_nav.portfolio_return or 0) / 100 + 1) * (1 + portfolio_daily) - 1 if first_nav else portfolio_daily
    benchmark_total = ((first_nav.benchmark_return or 0) / 100 + 1) * (1 + benchmark_daily) - 1 if first_nav else benchmark_daily

    db.add(PortfolioNav(
        nav_date=today,
        portfolio_return=round(portfolio_total * 100, 4),
        benchmark_return=round(benchmark_total * 100, 4),
        daily_return=round(portfolio_daily * 100, 4),
        benchmark_daily_return=round(benchmark_daily * 100, 4),
    ))
    db.commit()


def job():
    """定时执行的任务。"""
    provider = get_provider_name()
    max_stocks = int(get_config("max_stocks", "500"))
    print(f"[{datetime.now().isoformat()}] 开始定时选股任务 (provider={provider}, max_stocks={max_stocks})")
    db = SessionLocal()
    try:
        pipeline = ScreenerPipeline(provider_name=provider)
        result = pipeline.run(db, max_stocks=max_stocks)
        print(f"任务完成: {result}")

        # 选股完成后，预拉 Top 20 + 沪深300 的历史价格到本地缓存
        print(f"[{datetime.now().isoformat()}] 开始预热价格缓存...")
        price_service = PriceService(db)
        warm = price_service.warm_cache_for_snapshot(top_n=20, years=3)
        print(f"价格缓存预热完成: {warm['warmed_count']} 个标的, 区间 {warm['start_date']} ~ {warm['end_date']}")

        # 更新实盘组合净值
        print(f"[{datetime.now().isoformat()}] 更新实盘组合净值...")
        _update_portfolio_nav(db)
        print("实盘组合净值更新完成")
    except Exception as e:
        print(f"任务失败: {e}")
    finally:
        db.close()


# 每天 19:00 运行
schedule.every().day.at("19:00").do(job)

print("定时任务已启动，每天 19:00 运行。按 Ctrl+C 停止。")

while True:
    schedule.run_pending()
    time.sleep(60)
