"""历史行情数据服务：用于回测和补充当前行情。

设计原则：
- 优先用本地数据库（stock_prices 表）
- 缺失先走 BaoStock（免费、无频次限制、直接返回后复权价）
- BaoStock 失败时 Tushare / AkShare 兜底
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

import pandas as pd
from sqlalchemy.orm import Session

from backend.database.models import StockPrice
from backend.data import baostock_client
from backend.data.tushare_client import (
    fetch_hist_daily as tushare_fetch_hist_daily,
    fetch_adj_factor as tushare_fetch_adj_factor,
    to_adj_close as tushare_to_adj_close,
    normalize_tushare_symbol,
    fetch_index_daily as tushare_fetch_index_daily,
)


class PriceService:
    """统一的历史行情服务。"""

    def __init__(self, db: Session):
        self.db = db

    def get_adj_close(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> Optional[pd.DataFrame]:
        """获取某只股票某时间段的后复权日线。"""
        # 1. 查本地数据库
        local = self._query_local(symbol, start_date, end_date)
        if local is not None and len(local) > 0:
            return local

        # 2. 优先走 BaoStock（免费、无限流、直接后复权）
        df = baostock_client.fetch_hist_daily(symbol, start_date, end_date, adjust="2")
        if df is not None and not df.empty:
            self._cache_to_local(symbol, df, source="baostock")
            return df

        # 3. BaoStock 失败兜底 Tushare
        ts_symbol = normalize_tushare_symbol(symbol)
        try:
            daily_map = tushare_fetch_hist_daily([ts_symbol], start_date, end_date)
        except RuntimeError:
            daily_map = {}
        daily = daily_map.get(ts_symbol)
        if daily is None or daily.empty:
            return None

        try:
            adj_map = tushare_fetch_adj_factor([ts_symbol])
        except RuntimeError:
            adj_map = {}
        adj = adj_map.get(ts_symbol)
        if adj is not None and not adj.empty:
            daily = tushare_to_adj_close(daily, adj)
        else:
            daily["adj_close"] = daily["close"].astype(float)
            daily["adj_open"] = daily["open"].astype(float)

        self._cache_to_local(symbol, daily, source="tushare")
        return daily

    def get_index_return(
        self,
        index_code: str,
        start_date: str,
        end_date: str,
    ) -> Optional[float]:
        """计算指数在区间内的收益率。优先本地、再 BaoStock、再 AkShare。"""
        local = self._query_local(index_code, start_date, end_date)
        if local is not None and len(local) >= 2:
            return self._calc_return_from_df(local)

        # 走 BaoStock
        df = baostock_client.fetch_index_daily(index_code, start_date, end_date)
        if df is None or len(df) < 2:
            # AkShare 兜底
            df = self._fetch_index_via_akshare(index_code, start_date, end_date)
        if df is None or len(df) < 2:
            # Tushare 最后兜底
            try:
                df = tushare_fetch_index_daily(index_code, start_date, end_date)
                if df is not None and not df.empty:
                    df["close"] = df["close"].astype(float)
                    df["adj_close"] = df["close"]
                    df["adj_open"] = df["open"].astype(float)
                    df["vol"] = df.get("vol", 0)
            except RuntimeError:
                return None
        if df is None or len(df) < 2:
            return None
        self._cache_to_local(index_code, df, source="baostock")
        return self._calc_return_from_df(df)

    @staticmethod
    def _fetch_index_via_akshare(index_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """用 AkShare 拉沪深300等指数日线。index_code 例: 000300.SH"""
        try:
            import akshare as ak
            code = index_code.split(".")[0]
            sd = start_date.replace("-", "")
            ed = end_date.replace("-", "")
            df = ak.index_zh_a_hist(symbol=code, period="daily", start_date=sd, end_date=ed)
            if df is None or df.empty:
                return None
            df = df.rename(columns={
                "日期": "trade_date", "开盘": "open", "收盘": "close",
                "最高": "high", "最低": "low", "成交量": "vol",
            })
            df["trade_date"] = df["trade_date"].astype(str).str.replace("-", "")
            df["close"] = df["close"].astype(float)
            df["open"] = df["open"].astype(float)
            df["adj_close"] = df["close"]
            df["adj_open"] = df["open"]
            return df
        except Exception as e:
            print(f"[AkShare] index {index_code} fetch failed: {e}")
            return None

    @staticmethod
    def _calc_return_from_df(df: pd.DataFrame) -> Optional[float]:
        if df is None or len(df) < 2:
            return None
        df = df.sort_values("trade_date").reset_index(drop=True)
        start_price = float(df["adj_close"].iloc[0])
        end_price = float(df["adj_close"].iloc[-1])
        if start_price <= 0:
            return None
        return round((end_price - start_price) / start_price * 100, 2)

    def _query_local(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")
        rows = (
            self.db.query(StockPrice)
            .filter(StockPrice.symbol == symbol)
            .filter(StockPrice.trade_date >= sd)
            .filter(StockPrice.trade_date <= ed)
            .order_by(StockPrice.trade_date)
            .all()
        )
        if not rows:
            return None
        return pd.DataFrame([
            {
                "trade_date": r.trade_date,
                "open": r.open,
                "high": r.high,
                "low": r.low,
                "close": r.close,
                "adj_open": r.adj_open,
                "adj_close": r.adj_close,
                "volume": r.volume,
            }
            for r in rows
        ])

    def _cache_to_local(self, symbol: str, df: pd.DataFrame, source: str = "baostock"):
        """把外部数据源拉到的数据写入本地表。"""
        for _, row in df.iterrows():
            existing = (
                self.db.query(StockPrice)
                .filter(StockPrice.symbol == symbol)
                .filter(StockPrice.trade_date == str(row["trade_date"]))
                .first()
            )
            if existing:
                continue
            self.db.add(StockPrice(
                symbol=symbol,
                trade_date=str(row["trade_date"]),
                open=float(row["open"]) if pd.notna(row.get("open")) else None,
                high=float(row["high"]) if pd.notna(row.get("high")) else None,
                low=float(row["low"]) if pd.notna(row.get("low")) else None,
                close=float(row["close"]) if pd.notna(row.get("close")) else None,
                adj_open=float(row["adj_open"]) if pd.notna(row.get("adj_open")) else None,
                adj_close=float(row["adj_close"]) if pd.notna(row.get("adj_close")) else None,
                volume=float(row["vol"]) if pd.notna(row.get("vol")) else None,
                source=source,
            ))
        self.db.commit()