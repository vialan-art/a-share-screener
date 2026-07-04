"""Generate static A-share stock -> industry / sector JSON maps via AkShare.

Sources (in order):
1. akshare.stock_classify_sina()     (Sina industry classification, preferred)
2. akshare.stock_board_industry_name_em() + stock_board_industry_cons_em()
3. akshare.stock_industry_change_cninfo() for individual gap filling
"""
import json
import os
import random
import time
from collections import Counter
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

import akshare as ak
import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
INDUSTRY_FILE = os.path.join(DATA_DIR, "static_industry_map.json")
SECTOR_FILE = os.path.join(DATA_DIR, "static_sector_map.json")

RETRIES = 5
BASE_DELAY = 2.0
MAX_DELAY = 30.0


def retry_akshare(max_retries: int = RETRIES):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    if attempt == max_retries - 1:
                        raise
                    delay = min(BASE_DELAY * (2 ** attempt), MAX_DELAY)
                    delay = delay * (1 + random.uniform(-0.2, 0.2))
                    print(f"[retry] {func.__name__} attempt {attempt + 1}/{max_retries} failed: {type(e).__name__}: {str(e)[:80]}. Sleeping {delay:.1f}s...")
                    time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator

# Simple keyword-based industry -> broad sector mapping.
# Kept minimal; tune when real taxonomy changes.
SECTOR_KEYWORDS: List[Tuple[str, str]] = [
    ("银行", "金融"),
    ("保险", "金融"),
    ("证券", "金融"),
    ("期货", "金融"),
    ("信托", "金融"),
    ("金融", "金融"),
    ("互金", "金融"),
    ("半导", "科技"),
    ("芯片", "科技"),
    ("软件", "科技"),
    ("IT", "科技"),
    ("互联网", "科技"),
    ("通信", "科技"),
    ("计算机", "科技"),
    ("电子", "科技"),
    ("人工智能", "科技"),
    ("云", "科技"),
    ("大数据", "科技"),
    ("光伏", "新能源"),
    ("风电", "新能源"),
    ("储能", "新能源"),
    ("锂电", "新能源"),
    ("电池", "新能源"),
    ("新能源", "新能源"),
    ("电力", "能源"),
    ("煤炭", "能源"),
    ("石油", "能源"),
    ("天然气", "能源"),
    ("燃气", "能源"),
    ("能源", "能源"),
    ("有色", "材料"),
    ("钢铁", "材料"),
    ("化工", "材料"),
    ("化学", "材料"),
    ("建材", "材料"),
    ("水泥", "材料"),
    ("玻璃", "材料"),
    ("造纸", "材料"),
    ("橡胶", "材料"),
    ("塑料", "材料"),
    ("金属", "材料"),
    ("矿产", "材料"),
    ("新材料", "材料"),
    ("医药", "医药"),
    ("医疗", "医药"),
    ("生物", "医药"),
    ("中药", "医药"),
    ("医疗器械", "医药"),
    ("食品饮料", "消费"),
    ("白酒", "消费"),
    ("啤酒", "消费"),
    ("家电", "消费"),
    ("汽车", "消费"),
    ("零售", "消费"),
    ("商贸", "消费"),
    ("餐饮", "消费"),
    ("旅游", "消费"),
    ("酒店", "消费"),
    ("传媒", "消费"),
    ("娱乐", "消费"),
    ("纺织", "消费"),
    ("服装", "消费"),
    ("家具", "消费"),
    ("农业", "消费"),
    ("养殖", "消费"),
    ("种植", "消费"),
    ("房地产", "房地产"),
    ("地产", "房地产"),
    ("建筑", "工业"),
    ("工程", "工业"),
    ("机械", "工业"),
    ("设备", "工业"),
    ("制造", "工业"),
    ("军工", "工业"),
    ("航天", "工业"),
    ("航空", "工业"),
    ("船舶", "工业"),
    ("港口", "工业"),
    ("物流", "工业"),
    ("运输", "工业"),
    ("铁路", "工业"),
    ("公路", "工业"),
    ("机场", "工业"),
    ("环保", "公用事业"),
    ("水务", "公用事业"),
    ("公用", "公用事业"),
]


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


@retry_akshare()
def _ak_stock_info_a_code_name() -> pd.DataFrame:
    return ak.stock_info_a_code_name()


@retry_akshare()
def _ak_stock_classify_sina() -> pd.DataFrame:
    return ak.stock_classify_sina()


@retry_akshare()
def _ak_stock_board_industry_name_em() -> pd.DataFrame:
    return ak.stock_board_industry_name_em()


@retry_akshare()
def _ak_stock_board_industry_cons_em(symbol: str) -> pd.DataFrame:
    return ak.stock_board_industry_cons_em(symbol=symbol)


@retry_akshare()
def _ak_stock_industry_change_cninfo(symbol: str) -> pd.DataFrame:
    return ak.stock_industry_change_cninfo(symbol=symbol)


def _symbol_to_6digit(symbol: str) -> Optional[str]:
    """Normalize various symbol formats to 6-digit code."""
    if not symbol or not isinstance(symbol, str):
        return None
    s = symbol.strip().lower()
    # sh600000 / sz000001 / bj430047
    if len(s) >= 8 and s[:2] in ("sh", "sz", "bj"):
        s = s[2:]
    # Keep only trailing digits
    digits = "".join(ch for ch in s if ch.isdigit())
    if len(digits) == 6:
        return digits
    return None


def get_a_share_symbols() -> set:
    """Return the set of all valid 6-digit A-share codes."""
    print("[1/4] Fetching A-share stock list...")
    df = _ak_stock_info_a_code_name()
    codes = set()
    for c in df["code"]:
        sym = _symbol_to_6digit(str(c))
        if sym:
            codes.add(sym)
    print(f"[1/4] Valid A-share codes: {len(codes)}")
    return codes


def build_from_sina(valid_codes: set) -> Tuple[Dict[str, str], List[str]]:
    """Use akshare.stock_classify_sina() to build the mapping."""
    errors: List[str] = []
    mapping: Dict[str, str] = {}
    print("[2/4] Trying Sina classification (akshare.stock_classify_sina)...")
    try:
        df = _ak_stock_classify_sina()
        print(f"[2/4] Sina returned {len(df)} rows, {df['class'].nunique()} classes")
        required = {"code", "class"}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Missing columns: {missing}")

        for _, row in df.iterrows():
            sym = _symbol_to_6digit(str(row["code"]))
            industry = str(row["class"]).strip()
            if sym and industry and sym in valid_codes:
                # Sina is fine-grained; keep the first encountered classification.
                if sym not in mapping:
                    mapping[sym] = industry
        print(f"[2/4] Sina mapped {len(mapping)} A-share symbols")
    except Exception as e:
        err = f"Sina classification failed: {type(e).__name__}: {e}"
        print("[2/4]", err)
        errors.append(err)
    return mapping, errors


def build_from_eastmoney(valid_codes: set, existing: Dict[str, str]) -> Tuple[Dict[str, str], List[str]]:
    """Fill gaps using East Money industry boards."""
    errors: List[str] = []
    missing = valid_codes - set(existing.keys())
    if not missing:
        print("[3/4] East Money fallback skipped: no missing symbols")
        return existing, errors

    print(f"[3/4] East Money fallback for {len(missing)} missing symbols...")
    try:
        boards = _ak_stock_board_industry_name_em()
        if "板块名称" not in boards.columns or "板块代码" not in boards.columns:
            raise ValueError("Unexpected board columns: " + str(boards.columns.tolist()))

        board_rows = boards[["板块名称", "板块代码"]].to_dict("records")
        print(f"[3/4] Discovered {len(board_rows)} industry boards")

        filled = 0
        for idx, row in enumerate(board_rows):
            board_name = str(row["板块名称"]).strip()
            board_code = str(row["板块代码"]).strip()
            if not board_code.startswith("BK"):
                continue
            try:
                cons = _ak_stock_board_industry_cons_em(symbol=board_code)
                if cons is None or cons.empty or "代码" not in cons.columns:
                    continue
                for _, r in cons.iterrows():
                    sym = _symbol_to_6digit(str(r["代码"]))
                    if sym and sym in missing:
                        existing[sym] = board_name
                        missing.discard(sym)
                        filled += 1
                if (idx + 1) % 10 == 0:
                    _sleep(0.5)
            except Exception as e:
                err = f"Board {board_name} ({board_code}): {type(e).__name__}: {e}"
                errors.append(err)
                if (idx + 1) % 10 == 0:
                    _sleep(0.5)
                continue

        print(f"[3/4] East Money filled {filled} symbols; remaining missing: {len(missing)}")
    except Exception as e:
        err = f"East Money fallback failed: {type(e).__name__}: {e}"
        print("[3/4]", err)
        errors.append(err)

    return existing, errors


def build_from_cninfo(valid_codes: set, existing: Dict[str, str], max_symbols: Optional[int] = None) -> Tuple[Dict[str, str], List[str]]:
    """Fill remaining gaps with CNINFO individual industry lookups."""
    errors: List[str] = []
    missing = sorted(valid_codes - set(existing.keys()))
    if not missing:
        print("[4/4] CNINFO fallback skipped: no missing symbols")
        return existing, errors

    target = missing[:max_symbols] if max_symbols else missing
    print(f"[4/4] CNINFO fallback for {len(target)} symbols (申银万国/中证)...")

    filled = 0
    for i, sym in enumerate(target):
        try:
            # Try Shenyin Wanguo classification first, then CSI as fallback.
                for std in ("申银万国行业分类标准", "中证行业分类"):
                    df = _ak_stock_industry_change_cninfo(symbol=sym)
                    if df is None or df.empty:
                        continue
                # The exact column names vary by akshare version; inspect.
                col_std = None
                col_ind = None
                for c in df.columns:
                    lc = str(c).lower()
                    if "标准" in str(c) or "standard" in lc or "分类标准" in str(c):
                        col_std = c
                    if "行业" in str(c) and "名称" in str(c):
                        col_ind = c
                if col_ind:
                    if col_std:
                        mask = df[col_std].astype(str).str.contains(std.replace("行业分类标准", ""), na=False)
                        rows = df[mask]
                    else:
                        rows = df
                    if not rows.empty:
                        industry = str(rows.iloc[0][col_ind]).strip()
                        if industry:
                            existing[sym] = industry
                            filled += 1
                            break
        except Exception as e:
            err = f"CNINFO {sym}: {type(e).__name__}: {e}"
            errors.append(err)
        if (i + 1) % 50 == 0:
            print(f"[4/4] CNINFO progress {i + 1}/{len(target)}, filled {filled}")
            _sleep(0.5)

    print(f"[4/4] CNINFO filled {filled} symbols")
    return existing, errors


def industry_to_sector(industry: str) -> str:
    if not industry:
        return "其他"
    ind = industry.strip()
    for keyword, sector in SECTOR_KEYWORDS:
        if keyword in ind:
            return sector
    return "其他"


def main() -> None:
    start = time.time()
    errors: List[str] = []

    valid_codes = get_a_share_symbols()
    industry_map, errs1 = build_from_sina(valid_codes)
    errors.extend(errs1)

    industry_map, errs2 = build_from_eastmoney(valid_codes, industry_map)
    errors.extend(errs2)

    industry_map, errs3 = build_from_cninfo(valid_codes, industry_map)
    errors.extend(errs3)

    # Build sector map from final industry map
    sector_map: Dict[str, str] = {}
    for sym, industry in industry_map.items():
        sector_map[sym] = industry_to_sector(industry)

    # Ensure all valid codes appear in the JSON (empty string if truly unknown)
    for sym in valid_codes:
        if sym not in industry_map:
            industry_map[sym] = ""
        if sym not in sector_map:
            sector_map[sym] = "其他"

    # Write files
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(INDUSTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(industry_map, f, ensure_ascii=False, indent=2)
    with open(SECTOR_FILE, "w", encoding="utf-8") as f:
        json.dump(sector_map, f, ensure_ascii=False, indent=2)

    # Stats
    nonempty = {k: v for k, v in industry_map.items() if v}
    unique_industries = sorted(set(nonempty.values()))
    counter = Counter(nonempty.values())
    top10 = counter.most_common(10)

    print("\n=== Generation Summary ===")
    print(f"Total valid A-share codes: {len(valid_codes)}")
    print(f"Symbols mapped to industry: {len(nonempty)} ({len(nonempty)/len(valid_codes)*100:.1f}%)")
    print(f"Unique industries: {len(unique_industries)}")
    print(f"Top 10 industries:")
    for ind, cnt in top10:
        print(f"  {ind}: {cnt}")
    print(f"Errors/warnings: {len(errors)}")
    for err in errors[:10]:
        print(f"  - {err}")
    if len(errors) > 10:
        print(f"  ... and {len(errors) - 10} more")
    print(f"Files saved:\n  {INDUSTRY_FILE}\n  {SECTOR_FILE}")
    print(f"Elapsed: {time.time() - start:.1f}s")


if __name__ == "__main__":
    main()
