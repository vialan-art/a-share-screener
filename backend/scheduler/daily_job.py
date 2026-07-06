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
    """更新实盘组合净值。取最新的 Portfolio 作为当前持仓，计算今日收益。

    支持从组合成立日开始连续累计，并在首次调用时自动回填历史 NAV。
    """
    latest_portfolio = db.query(Portfolio).order_by(Portfolio.portfolio_date.desc()).first()
    if not latest_portfolio:
        return

    portfolio_date = latest_portfolio.portfolio_date
    items = db.query(Portfolio).filter(Portfolio.portfolio_date == portfolio_date).all()
    if not items:
        return

    symbols = [i.symbol for i in items]

    def _latest_price(symbol, date_str):
        return db.query(StockPrice).filter(
            StockPrice.symbol == symbol,
            StockPrice.trade_date <= date_str.replace("-", ""),
        ).order_by(StockPrice.trade_date.desc()).first()

    def _daily_return(symbol, today_str, yesterday_str):
        t = _latest_price(symbol, today_str)
        y = _latest_price(symbol, yesterday_str)
        if t and y and y.adj_close and y.adj_close > 0:
            return (t.adj_close - y.adj_close) / y.adj_close
        return None

    # 自动回填从组合成立日（portfolio_date）到昨天的历史 NAV
    existing_dates = {r[0] for r in db.query(PortfolioNav.nav_date).all()}
    start = datetime.strptime(portfolio_date, "%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    current = start
    prev_date = None
    cumulative_port = None
    cumulative_bench = None

    while current.strftime("%Y-%m-%d") <= yesterday:
        date_str = current.strftime("%Y-%m-%d")
        if date_str in existing_dates:
            # 同步累计基数，使后续日期能继续连乘
            nav = db.query(PortfolioNav).filter(PortfolioNav.nav_date == date_str).first()
            cumulative_port = (nav.portfolio_return or 0) / 100
            cumulative_bench = (nav.benchmark_return or 0) / 100
            prev_date = date_str
            current += timedelta(days=1)
            continue

        if prev_date is None:
            # 成立日没有前一日收益，NAV 从 0 开始
            db.add(PortfolioNav(
                nav_date=date_str,
                portfolio_return=0.0,
                benchmark_return=0.0,
                daily_return=0.0,
                benchmark_daily_return=0.0,
            ))
            db.commit()
            cumulative_port = 0.0
            cumulative_bench = 0.0
            existing_dates.add(date_str)
            prev_date = date_str
            current += timedelta(days=1)
            continue

        returns = []
        for symbol in symbols:
            r = _daily_return(symbol, date_str, prev_date)
            if r is not None:
                returns.append(r)
        port_daily = sum(returns) / len(returns) if returns else None

        bench_daily = _daily_return("000300.SH", date_str, prev_date)

        if port_daily is None or bench_daily is None:
            # 非交易日，跳过
            current += timedelta(days=1)
            continue

        cumulative_port = (1 + cumulative_port) * (1 + port_daily) - 1
        cumulative_bench = (1 + cumulative_bench) * (1 + bench_daily) - 1
        db.add(PortfolioNav(
            nav_date=date_str,
            portfolio_return=round(cumulative_port * 100, 4),
            benchmark_return=round(cumulative_bench * 100, 4),
            daily_return=round(port_daily * 100, 4),
            benchmark_daily_return=round(bench_daily * 100, 4),
        ))
        db.commit()
        existing_dates.add(date_str)
        prev_date = date_str
        current += timedelta(days=1)

    # 更新今日 NAV
    today = datetime.now().strftime("%Y-%m-%d")
    if today in existing_dates:
        return

    returns = []
    for symbol in symbols:
        r = _daily_return(symbol, today, yesterday)
        if r is not None:
            returns.append(r)
    if not returns:
        return
    port_daily = sum(returns) / len(returns)
    bench_daily = _daily_return("000300.SH", today, yesterday) or 0.0

    latest_nav = db.query(PortfolioNav).order_by(PortfolioNav.nav_date.desc()).first()
    if latest_nav:
        cumulative_port = ((latest_nav.portfolio_return or 0) / 100 + 1) * (1 + port_daily) - 1
        cumulative_bench = ((latest_nav.benchmark_return or 0) / 100 + 1) * (1 + bench_daily) - 1
    else:
        cumulative_port = port_daily
        cumulative_bench = bench_daily

    db.add(PortfolioNav(
        nav_date=today,
        portfolio_return=round(cumulative_port * 100, 4),
        benchmark_return=round(cumulative_bench * 100, 4),
        daily_return=round(port_daily * 100, 4),
        benchmark_daily_return=round(bench_daily * 100, 4),
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

        # 为滚动回测预热所有历史快照的 Top N
        print(f"[{datetime.now().isoformat()}] 开始预热滚动回测价格缓存...")
        warm_all = price_service.warm_cache_for_all_snapshots(top_n=20, years=3)
        print(f"滚动回测缓存预热完成: {warm_all.get('warmed_count', 0)} 个标的, {warm_all.get('snapshot_count', 0)} 个快照")

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
