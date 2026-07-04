"""批量预热历史价格缓存。

用途：一次性把全市场股票（或指定列表）的 N 年历史日线拉进本地 stock_prices 表，
让回测、复盘无需再调外部接口。

运行方式（在 backend 目录下）：
    python -m backend.scripts.warm_prices --years 3 --limit 0

参数：
    --years: 拉取历史年数，默认 3
    --limit: 0 表示全市场，>0 表示只预热前 N 只
    --index: 同时预热沪深300，默认开启
    --batch: 每批处理的股票数量，默认 100（BaoStock 单 session 建议不超过 300）
"""
import argparse
import sys
import os
from datetime import datetime, timedelta


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.database.connection import SessionLocal
from backend.data.price_service import PriceService
from backend.data.akshare_provider import AkShareProvider
from backend.data.baostock_client import fetch_hist_daily_batch


def main():
    parser = argparse.ArgumentParser(description="预热股票历史价格缓存")
    parser.add_argument("--years", type=int, default=3, help="历史年数")
    parser.add_argument("--limit", type=int, default=0, help="限制股票数量，0=全市场")
    parser.add_argument("--index", action="store_true", default=True, help="是否预热沪深300")
    parser.add_argument("--batch", type=int, default=100, help="BaoStock 批量 session 大小")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        service = PriceService(db)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_dt = datetime.now() - timedelta(days=365 * args.years)
        start_date = start_dt.strftime("%Y-%m-%d")

        # 获取股票列表
        provider = AkShareProvider()
        stocks = provider.get_stock_list()
        if args.limit > 0:
            stocks = stocks[:args.limit]
        symbols = [s["symbol"] for s in stocks]
        print(f"准备预热 {len(symbols)} 只股票，区间 {start_date} ~ {end_date}")

        success = 0
        fail = 0
        for i in range(0, len(symbols), args.batch):
            batch = symbols[i:i + args.batch]
            try:
                batch_result = fetch_hist_daily_batch(batch, start_date, end_date, adjust="2")
                for symbol, df in batch_result.items():
                    if df is not None and not df.empty:
                        service._cache_to_local(symbol, df, source="baostock")
                        success += 1
                    else:
                        fail += 1
                print(f"  已处理 {min(i + args.batch, len(symbols))}/{len(symbols)}，成功 {success}，失败 {fail}")
            except Exception as e:
                print(f"[warm_prices] batch {i}-{i+args.batch} failed: {e}")
                fail += len(batch)

        # 沪深300
        if args.index:
            try:
                service.get_index_return("000300.SH", start_date, end_date)
                print("沪深300 预热完成")
            except Exception as e:
                print(f"沪深300 预热失败: {e}")

        print(f"\n完成: 成功 {success}，失败 {fail}，共 {len(symbols)}")
    finally:
        db.close()


if __name__ == "__main__":
    main()