"""为插件信号批量获取 K 线数据。"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from backend.data.price_service import PriceService


class PluginDataService:
    """给插件层提供 OHLCV 数据，优先读本地缓存。"""

    def __init__(self, db: Session):
        self.price_service = PriceService(db)

    def fetch_ohlcv(
        self,
        symbol: str,
        days: int = 300,
        end_date: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """获取一只股票的近期 OHLCV，返回列表（最新在最后）。"""
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
        start_dt = datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days + 30)
        start_date = start_dt.strftime("%Y-%m-%d")

        df = self.price_service.get_adj_close(symbol, start_date=start_date.replace("-", ""), end_date=end_date.replace("-", ""))
        if df is None or df.empty:
            return None

        df = df.sort_values("trade_date").reset_index(drop=True)
        # BaoStock 返回 amount 字段表示成交额（元）
        if "amount" in df.columns and "turnover" not in df.columns:
            df = df.rename(columns={"amount": "turnover"})
        # 统一列名：BaoStock 返回 vol，Tushare 可能返回 vol，这里统一为 volume
        if "vol" in df.columns and "volume" not in df.columns:
            df = df.rename(columns={"vol": "volume"})
        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        if "close" not in df.columns or df["close"].isnull().all():
            return None

        # 只保留需要的列，缺失 volume/turnover 时填 0
        records = []
        for _, row in df.iterrows():
            rec = {
                "trade_date": str(row["trade_date"]),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row["volume"]) if "volume" in df.columns and pd.notna(row.get("volume")) else 0.0,
            }
            if "turnover" in df.columns and pd.notna(row.get("turnover")):
                rec["turnover"] = float(row["turnover"])
            records.append(rec)
        return records

    def fetch_batch(
        self,
        symbols: List[str],
        days: int = 300,
        end_date: Optional[str] = None,
    ) -> Dict[str, List[Dict]]:
        """批量获取，失败的股票返回空。"""
        result = {}
        for sym in symbols:
            try:
                data = self.fetch_ohlcv(sym, days, end_date)
                if data:
                    result[sym] = data
            except Exception as e:
                print(f"[PluginDataService] {sym} fetch failed: {e}")
                result[sym] = []
        return result
