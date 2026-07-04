"""BaoStock 数据补充模块。

相比 Tushare 的优势：
- 免费、无需 Token、无每分钟/每天频次限制
- query_history_k_data_plus 直接返回前/后复权价，不用自己拼 adj_factor
- 适合回测场景下的批量历史数据拉取

劣势：
- 接口风格啰嗦（必须 login/logout）
- 数据更新 T+1（前一交易日数据次日可得）
- 没有分红配送、龙虎榜、ST 标记等特色数据

设计：每次调用都 login → 查询 → logout，避免长连接被服务器踢。
"""
from contextlib import contextmanager
from typing import Optional, List

import pandas as pd


@contextmanager
def _baostock_session():
    """BaoStock 登录会话上下文管理器。"""
    import baostock as bs
    lg = bs.login()
    try:
        yield bs
    finally:
        bs.logout()


def _to_baostock_code(symbol: str) -> str:
    """内部 000001 / 000001.SZ 格式转 BaoStock 的 sh.600000 / sz.000001 格式。"""
    s = symbol.strip().zfill(6)
    # 已经是 SH/SZ 后缀的情况
    if "." in symbol:
        code, suffix = symbol.split(".")
        code = code.zfill(6)
        return f"{suffix.lower()}.{code}"
    # 仅 6 位代码，按规则推断交易所
    if s.startswith(("6", "68", "88", "89")):
        return f"sh.{s}"
    elif s.startswith(("0", "3", "2")):
        return f"sz.{s}"
    elif s.startswith(("8", "4")):
        return f"bj.{s}"
    return f"sz.{s}"


def _normalize_trade_date(d: str) -> str:
    """统一日期格式为 YYYY-MM-DD（BaoStock 要求）。"""
    d = str(d).strip()
    if "-" in d:
        return d
    if len(d) == 8:
        return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
    return d


def _trade_date_to_yyyymmdd(d: str) -> str:
    """YYYY-MM-DD 转 YYYYMMDD（本地存储用）。"""
    return str(d).replace("-", "")


def fetch_hist_daily(
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: str = "2",
) -> Optional[pd.DataFrame]:
    """拉单只股票后复权日线。

    Args:
        symbol: 内部格式 000001 / 000001.SZ
        start_date / end_date: 支持 YYYY-MM-DD 或 YYYYMMDD
        adjust: "1" 前复权 / "2" 后复权 / "3" 不复权

    Returns:
        DataFrame 列：trade_date(YYYYMMDD), open, high, low, close,
                       adj_open, adj_close, vol
    """
    bs_code = _to_baostock_code(symbol)
    sd = _normalize_trade_date(start_date)
    ed = _normalize_trade_date(end_date)

    fields = "date,open,high,low,close,volume,amount,adjustflag,preclose,isST"
    try:
        with _baostock_session() as bs:
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields,
                start_date=sd,
                end_date=ed,
                frequency="d",
                adjustflag=adjust,
            )
            if rs.error_code != "0":
                print(f"[BaoStock] {symbol} error: {rs.error_code} {rs.error_msg}")
                return None
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=rs.fields)
    except Exception as e:
        print(f"[BaoStock] {symbol} fetch failed: {e}")
        return None

    # 数据清洗
    df["trade_date"] = df["date"].apply(_trade_date_to_yyyymmdd)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    # BaoStock 后复权返回的 close 就是后复权收盘价
    df["adj_close"] = df["close"]
    df["adj_open"] = df["open"]
    df["vol"] = df["volume"]
    return df[["trade_date", "open", "high", "low", "close",
             "adj_open", "adj_close", "vol", "isST"]]


def fetch_index_daily(
    index_code: str,
    start_date: str,
    end_date: str,
) -> Optional[pd.DataFrame]:
    """拉指数日线。index_code 例: 000300.SH → BaoStock 的 sh.000300"""
    bs_code = _to_baostock_code(index_code)
    sd = _normalize_trade_date(start_date)
    ed = _normalize_trade_date(end_date)

    fields = "date,open,high,low,close,volume,amount"
    try:
        with _baostock_session() as bs:
            rs = bs.query_history_k_data_plus(
                bs_code,
                fields,
                start_date=sd,
                end_date=ed,
                frequency="d",
                adjustflag="3",
            )
            if rs.error_code != "0":
                print(f"[BaoStock] index {index_code} error: {rs.error_code} {rs.error_msg}")
                return None
            rows = []
            while rs.next():
                rows.append(rs.get_row_data())
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=rs.fields)
    except Exception as e:
        print(f"[BaoStock] index {index_code} fetch failed: {e}")
        return None

    df["trade_date"] = df["date"].apply(_trade_date_to_yyyymmdd)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["adj_close"] = df["close"]
    df["adj_open"] = df["open"]
    df["vol"] = df["volume"]
    return df[["trade_date", "open", "high", "low", "close",
             "adj_open", "adj_close", "vol"]]