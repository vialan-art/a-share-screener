"""每日定时任务调度器。

用 schedule 库每天 19:00 运行一次选股流程。
可以在服务器上长期运行这个脚本。
"""
import os
import schedule
import time
from datetime import datetime

from backend.database.connection import SessionLocal
from backend.pipeline import ScreenerPipeline
from backend.config import get_provider_name, get_config
from backend.data.price_service import PriceService


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
