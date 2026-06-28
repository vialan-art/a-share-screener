"""每日定时任务调度器。

用 schedule 库每天 19:00 运行一次选股流程。
可以在服务器上长期运行这个脚本。
"""
import schedule
import time
from datetime import datetime

from backend.database.connection import SessionLocal
from backend.pipeline import ScreenerPipeline


def job():
    """定时执行的任务。"""
    print(f"[{datetime.now().isoformat()}] 开始定时选股任务")
    db = SessionLocal()
    try:
        pipeline = ScreenerPipeline()
        result = pipeline.run(db, max_stocks=500)
        print(f"任务完成: {result}")
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
