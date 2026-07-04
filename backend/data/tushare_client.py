"""Tushare 数据补充模块。

用途：
1. 拿历史日线行情（后复权），用于回测。
2. 作为 AkShare 的补充数据源，不替代现有 pipeline。
3. 优先从 TUSHARE_TOKEN 环境变量读取；否则从数据库 app_configs 表读取。
"""
import os
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd


ENV_TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")


def _get_token_from_db() -> Optional[str]:
    """从数据库设置表读取 Tushare Token。"""
    try:
        from backend.database.connection import SessionLocal
        from backend.database.models import AppConfig
        db = SessionLocal()
        try:
            row = db.query(AppConfig).filter(AppConfig.key == "tushare_token").first()
            return row.value.strip() if row and row.value else None
        finally:
            db.close()
    except Exception:
        return None


def get_tushare_token() -> str:
    """获取有效的 Tushare Token。"""
    token = ENV_TUSHARE_TOKEN or _get_token_from_db() or ""
    return token.strip()


def _get_tushare_pro():
    """延迟导入并初始化 tushare。"""
    import tushare as ts
    token = get_tushare_token()
    if not token:
        raise RuntimeError("TUSHARE_TOKEN not set")
    ts.set_token(token)
    return ts.pro_api()


def fetch_hist_daily(symbols: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
    """获取多只股票的后复权日线行情。

    Args:
        symbols: 股票代码列表，如 ["000001.SZ", "600000.SH"]
        start_date: 开始日期 "YYYYMMDD"
        end_date: 结束日期 "YYYYMMDD"

    Returns:
        {symbol: DataFrame}，DataFrame 列：trade_date, open, high, low, close, vol
    """
    pro = _get_tushare_pro()
    result = {}
    for symbol in symbols:
        try:
            df = pro.daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date,
            )
            if df is not None and not df.empty:
                df = df.sort_values("trade_date").reset_index(drop=True)
                result[symbol] = df
            time.sleep(0.2)  # 免费版限流
        except Exception as e:
            print(f"[Tushare] {symbol} daily fetch failed: {e}")
    return result


def fetch_adj_factor(symbols: List[str]) -> Dict[str, pd.DataFrame]:
    """获取复权因子，用于把收盘价转成后复权价。"""
    pro = _get_tushare_pro()
    result = {}
    for symbol in symbols:
        try:
            df = pro.adj_factor(ts_code=symbol)
            if df is not None and not df.empty:
                df = df.sort_values("trade_date").reset_index(drop=True)
                result[symbol] = df
            time.sleep(0.2)
        except Exception as e:
            print(f"[Tushare] {symbol} adj_factor fetch failed: {e}")
    return result


def to_adj_close(daily_df: pd.DataFrame, adj_df: pd.DataFrame) -> pd.DataFrame:
    """用后复权因子把 close 转成后复权 close。"""
    df = daily_df.merge(adj_df[["trade_date", "adj_factor"]], on="trade_date", how="left")
    df["adj_factor"] = df["adj_factor"].astype(float)
    df["adj_close"] = df["close"].astype(float) * df["adj_factor"]
    df["adj_open"] = df["open"].astype(float) * df["adj_factor"]
    return df


def normalize_tushare_symbol(symbol: str) -> str:
    """把内部 000001 格式转成 Tushare 的 000001.SZ。"""
    s = symbol.strip().zfill(6)
    if s.startswith(("6", "68", "88", "89")):
        return f"{s}.SH"
    elif s.startswith(("0", "3", "2")):
        return f"{s}.SZ"
    elif s.startswith(("8", "4")):
        return f"{s}.BJ"
    return f"{s}.SZ"


def fetch_index_daily(index_code: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """获取指数日线，用于基准对比。index_code: 000300.SH 沪深300, 000001.SH 上证指数。"""
    pro = _get_tushare_pro()
    try:
        df = pro.index_daily(ts_code=index_code, start_date=start_date, end_date=end_date)
        if df is not None and not df.empty:
            return df.sort_values("trade_date").reset_index(drop=True)
    except Exception as e:
        print(f"[Tushare] index {index_code} fetch failed: {e}")
    return None
