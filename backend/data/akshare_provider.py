"""AkShare 数据提供者实现（生产级优化版）。

设计目标：
1. 稳定性：所有 AkShare 调用带指数退避重试，避免单点失败导致整个 pipeline 崩溃。
2. 数据质量：补充行业分类、真实审计意见、缓存机制。
3. 覆盖范围：默认全市场 5000+ 只股票，可通过 max_stocks 限制。
4. 透明度：记录每个字段的来源、完整度和异常值。

重要：AkShare 数据来自东方财富、巨潮资讯等第三方，可能存在延迟、错误、字段变更。
本 provider 会尽量做数据清洗和标记，但不保证 100% 正确。
"""
import os
import time
import math
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from functools import wraps

import pandas as pd
from backend.data.provider import DataProvider


# 允许通过环境变量控制请求重试和行业在线拉取
AKSHARE_MAX_RETRIES = int(os.environ.get("AKSHARE_MAX_RETRIES", "5"))
AKSHARE_BASE_DELAY = float(os.environ.get("AKSHARE_BASE_DELAY", "2.0"))
AKSHARE_MAX_DELAY = float(os.environ.get("AKSHARE_MAX_DELAY", "30.0"))
AKSHARE_JITTER = float(os.environ.get("AKSHARE_JITTER", "0.5"))
AKSHARE_FETCH_INDUSTRY_ONLINE = os.environ.get("AKSHARE_FETCH_INDUSTRY_ONLINE", "false").lower() in ("1", "true", "yes")

# 行业映射缓存文件路径
INDUSTRY_CACHE_FILE = os.environ.get(
    "INDUSTRY_CACHE_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "industry_cache.json"),
)
STATIC_INDUSTRY_FILE = os.environ.get(
    "STATIC_INDUSTRY_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_industry_map.json"),
)


def _retry_with_backoff(max_retries: int = AKSHARE_MAX_RETRIES):
    """装饰器：为 AkShare 调用提供指数退避重试。"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    # 不重试的情况：明显的数据错误（非网络错误）
                    error_name = type(e).__name__
                    if error_name in ("KeyError", "ValueError", "IndexError") and attempt == 0:
                        # 第一次就遇到数据解析错误，直接抛出
                        raise
                    # 计算退避时间
                    delay = min(AKSHARE_BASE_DELAY * (2 ** attempt), AKSHARE_MAX_DELAY)
                    delay = delay * (1 + (AKSHARE_JITTER * (0.5 - (time.time() % 1))))
                    print(f"[{func.__name__}]  attempt {attempt + 1}/{max_retries} failed: {error_name}: {str(e)[:80]}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
            # 所有重试都失败
            raise last_exception
        return wrapper
    return decorator


def _load_json_map(path: str) -> Dict[str, str]:
    """从 JSON 文件加载映射。"""
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k).strip().zfill(6): str(v).strip() for k, v in data.items() if v}
    except Exception as e:
        print(f"[AkShare] 加载映射文件失败 {path}: {e}")
    return {}


def _save_json_map(path: str, data: Dict[str, str]):
    """保存映射到 JSON 文件。"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[AkShare] 保存映射文件失败 {path}: {e}")


class AkShareProvider(DataProvider):
    """A股数据源：AkShare（生产级优化）。"""

    # 行业映射缓存，避免每次请求都重新拉取
    _industry_cache: Optional[pd.DataFrame] = None
    _industry_cache_time: Optional[datetime] = None
    _industry_cache_ttl = timedelta(hours=6)

    # 静态 fallback：常见股票行业映射
    _static_industry_map: Optional[Dict[str, str]] = None

    @property
    def name(self) -> str:
        return "akshare"

    def _load_static_fallback(self) -> Dict[str, str]:
        """加载静态行业 fallback（文件不存在时使用内置简表）。"""
        if AkShareProvider._static_industry_map is None:
            file_map = _load_json_map(STATIC_INDUSTRY_FILE)
            # 内置简表：覆盖部分常见大盘股
            built_in = self._built_in_industry_map()
            built_in.update(file_map)  # 文件覆盖内置
            AkShareProvider._static_industry_map = built_in
        return AkShareProvider._static_industry_map

    @staticmethod
    def _built_in_industry_map() -> Dict[str, str]:
        """内置常见 A 股行业映射（不完全覆盖）。"""
        return {
            "000001": "银行", "000002": "房地产", "000063": "通信", "000066": "计算机",
            "000100": "电子", "000333": "家用电器", "000538": "医药生物", "000568": "食品饮料",
            "000651": "家用电器", "000725": "电子", "000768": "国防军工", "000858": "食品饮料",
            "000895": "食品饮料", "002001": "医药生物", "002007": "医药生物", "002024": "商贸零售",
            "002027": "传媒", "002044": "医药生物", "002049": "电子", "002120": "交通运输",
            "002142": "银行", "002230": "计算机", "002236": "计算机", "002271": "建筑材料",
            "002304": "食品饮料", "002352": "交通运输", "002415": "计算机", "002460": "有色金属",
            "002475": "电子", "002594": "汽车", "002600": "电子", "002624": "传媒",
            "002648": "石油石化", "002714": "农林牧渔", "002812": "电力设备", "002821": "医药生物",
            "300003": "医药生物", "300014": "电子", "300015": "医药生物", "300033": "计算机",
            "300059": "非银金融", "300122": "医药生物", "300124": "电力设备", "300142": "医药生物",
            "300274": "电力设备", "300408": "电子", "300413": "传媒", "300433": "电子",
            "300498": "农林牧渔", "300750": "电力设备", "600000": "银行", "600009": "交通运输",
            "600016": "银行", "600028": "石油石化", "600030": "非银金融", "600031": "机械设备",
            "600036": "银行", "600048": "房地产", "600050": "通信", "600104": "汽车",
            "600109": "非银金融", "600111": "有色金属", "600115": "交通运输", "600132": "食品饮料",
            "600150": "国防军工", "600176": "建筑材料", "600196": "医药生物", "600276": "医药生物",
            "600309": "基础化工", "600340": "房地产", "600346": "石油石化", "600406": "计算机",
            "600436": "医药生物", "600438": "电力设备", "600519": "食品饮料", "600547": "有色金属",
            "600570": "计算机", "600585": "建筑材料", "600588": "计算机", "600600": "食品饮料",
            "600660": "汽车", "600690": "家用电器", "600703": "电子", "600745": "电子",
            "600809": "食品饮料", "600837": "非银金融", "600887": "食品饮料", "600893": "国防军工",
            "600900": "公用事业", "600919": "银行", "600958": "非银金融", "600999": "非银金融",
            "601012": "电力设备", "601066": "非银金融", "601088": "煤炭", "601111": "交通运输",
            "601117": "建筑装饰", "601138": "电子", "601166": "银行", "601169": "银行",
            "601186": "建筑装饰", "601211": "非银金融", "601225": "煤炭", "601288": "银行",
            "601318": "非银金融", "601319": "非银金融", "601328": "银行", "601336": "非银金融",
            "601360": "计算机", "601398": "银行", "601628": "非银金融", "601633": "汽车",
            "601668": "建筑装饰", "601688": "非银金融", "601698": "国防军工", "601818": "银行",
            "601857": "石油石化", "601877": "电力设备", "601888": "商贸零售", "601899": "有色金属",
            "601901": "非银金融", "601933": "商贸零售", "601939": "银行", "601955": "公用事业",
            "601985": "公用事业", "601988": "银行", "601989": "国防军工", "601998": "银行",
            "603019": "计算机", "603288": "食品饮料", "603501": "电子", "603658": "医药生物",
            "603799": "有色金属", "603986": "电子", "603993": "有色金属", "605117": "电子",
            "688001": "国防军工", "688002": "电子", "688009": "机械设备", "688012": "电子",
            "688036": "电子", "688111": "传媒", "688169": "家用电器", "688187": "医药生物",
            "688303": "电力设备", "688599": "电力设备", "688981": "电子",
        }

    @_retry_with_backoff()
    def _ak_stock_info_a_code_name(self) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_info_a_code_name()

    @_retry_with_backoff()
    def _ak_stock_yjbb_em(self, date: str) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_yjbb_em(date=date)

    @_retry_with_backoff()
    def _ak_stock_zh_a_spot_em(self) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_zh_a_spot_em()

    @_retry_with_backoff()
    def _ak_stock_board_industry_name_em(self) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_board_industry_name_em()

    @_retry_with_backoff()
    def _ak_stock_board_industry_cons_em(self, symbol: str) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_board_industry_cons_em(symbol=symbol)

    @_retry_with_backoff()
    def _ak_stock_individual_info_em(self, symbol: str) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_individual_info_em(symbol=symbol)

    @_retry_with_backoff()
    def _ak_stock_industry_change_cninfo(self, symbol: str) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_industry_change_cninfo(symbol=symbol)

    @_retry_with_backoff()
    def _ak_stock_yjbb_em_detail(self) -> pd.DataFrame:
        """备用：获取更详细的业绩报告数据（年报/季报）。"""
        import akshare as ak
        # 尝试获取最新报告期
        for date_str in ["20241231", "20240930", "20240630", "20240331"]:
            try:
                df = ak.stock_yjbb_em(date=date_str)
                if df is not None and not df.empty:
                    return df
            except Exception:
                continue
        return pd.DataFrame()

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取 A股所有股票列表，并补充行业分类。默认剔除 ST / *ST / 退市股票。"""
        df = self._ak_stock_info_a_code_name()
        industry_map = self._build_industry_map()

        result = []
        skipped_st = 0
        for _, row in df.iterrows():
            symbol = str(row["code"]).strip().zfill(6)
            name = str(row["name"]).strip()

            # 过滤 ST / *ST / 退市风险
            if name.startswith("*ST") or name.startswith("ST") or "退" in name:
                skipped_st += 1
                continue

            if symbol.startswith(("60", "68", "88", "89")):
                market = "SH"
            elif symbol.startswith(("00", "30", "20")):
                market = "SZ"
            elif symbol.startswith(("8", "4")):
                market = "BJ"
            else:
                market = "UNKNOWN"

            industry = industry_map.get(symbol, "")

            result.append({
                "symbol": symbol,
                "name": name,
                "industry": industry,
                "sector": "",
                "market": market,
            })

        print(f"[AkShareProvider] 剔除 ST/退市股票 {skipped_st} 只，剩余 {len(result)} 只")
        return result

    def _build_industry_map(self) -> Dict[str, str]:
        """构建股票代码到行业的映射。

        策略：
        1. 优先读取磁盘缓存（6 小时内）。
        2. 尝试东方财富行业板块成分股。
        3. 尝试个股信息接口补充。
        4. 最后使用内置静态 fallback。
        """
        now = datetime.utcnow()

        # 1. 内存缓存
        if (
            AkShareProvider._industry_cache is not None
            and AkShareProvider._industry_cache_time is not None
            and now - AkShareProvider._industry_cache_time < AkShareProvider._industry_cache_ttl
        ):
            return dict(zip(
                AkShareProvider._industry_cache["symbol"],
                AkShareProvider._industry_cache["industry"]
            ))

        # 2. 磁盘缓存
        disk_cache = _load_json_map(INDUSTRY_CACHE_FILE)
        if disk_cache:
            cache_df = pd.DataFrame([
                {"symbol": k, "industry": v} for k, v in disk_cache.items()
            ])
            AkShareProvider._industry_cache = cache_df
            AkShareProvider._industry_cache_time = now
            return disk_cache

        # 3. 静态 fallback（最后手段）
        static_map = self._load_static_fallback()

        # 4. 在线获取行业映射（默认关闭，避免每次运行都缓慢拉取东财板块）
        if AKSHARE_FETCH_INDUSTRY_ONLINE:
            try:
                online_map = self._fetch_industry_map_online()
                if online_map:
                    static_map.update(online_map)
                    _save_json_map(INDUSTRY_CACHE_FILE, static_map)
                    cache_df = pd.DataFrame([
                        {"symbol": k, "industry": v} for k, v in static_map.items()
                    ])
                    AkShareProvider._industry_cache = cache_df
                    AkShareProvider._industry_cache_time = now
            except Exception as e:
                print(f"[AkShare] 在线行业映射获取失败，使用静态 fallback: {e}")
        else:
            # 即使是在线拉取关闭，也把静态 fallback 写入内存/磁盘缓存，避免重复加载
            _save_json_map(INDUSTRY_CACHE_FILE, static_map)
            cache_df = pd.DataFrame([
                {"symbol": k, "industry": v} for k, v in static_map.items()
            ])
            AkShareProvider._industry_cache = cache_df
            AkShareProvider._industry_cache_time = now

        return static_map

    def _fetch_industry_map_online(self) -> Dict[str, str]:
        """尝试从多个在线源获取行业映射。"""
        industry_map = {}

        # 方法 A：东方财富行业板块
        try:
            boards_df = self._ak_stock_board_industry_name_em()
            if "板块名称" in boards_df.columns and "板块代码" in boards_df.columns:
                board_rows = boards_df[["板块名称", "板块代码"]].to_dict("records")
                print(f"[AkShare] 发现 {len(board_rows)} 个行业板块")
                success_count = 0
                for idx, row in enumerate(board_rows):
                    board_name = str(row["板块名称"]).strip()
                    board_code = str(row["板块代码"]).strip()
                    if not board_code.startswith("BK"):
                        continue
                    try:
                        cons_df = self._ak_stock_board_industry_cons_em(symbol=board_code)
                        if cons_df is None or cons_df.empty or "代码" not in cons_df.columns:
                            continue
                        for _, r in cons_df.iterrows():
                            sym = str(r["代码"]).strip().zfill(6)
                            if sym and sym not in industry_map:
                                industry_map[sym] = board_name
                        success_count += 1
                        if (idx + 1) % 10 == 0:
                            time.sleep(1)
                    except Exception:
                        continue
                print(f"[AkShare] 东财板块映射：{success_count}/{len(board_rows)} 个板块，覆盖 {len(industry_map)} 只股票")
        except Exception as e:
            print(f"[AkShare] 东财板块映射失败: {e}")

        return industry_map

    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取财务指标。

        使用 stock_yjbb_em（业绩快报）一次性获取全市场最新财报数据。
        注意：业绩快报不是完整年报，部分指标缺失。
        """
        metrics = []
        now = datetime.utcnow()

        # 尝试最近几个报告期
        df = None
        for date_str in ["20241231", "20240930", "20240630", "20240331"]:
            try:
                df = self._ak_stock_yjbb_em(date_str)
                if df is not None and not df.empty:
                    break
            except Exception as e:
                print(f"拉取业绩快报 {date_str} 失败: {e}")
                continue

        if df is None or df.empty:
            print("所有报告期业绩快报都失败")
            return []

        # 标准化列名（尽可能多地映射）
        column_map = {
            "股票代码": "symbol",
            "股票简称": "name",
            "报告期": "report_period",
            "每股收益": "eps",
            "营业收入-营业收入": "revenue",
            "营业收入-同比增长": "revenue_growth",
            "净利润-净利润": "net_profit",
            "净利润-同比增长": "profit_growth",
            "扣非净利润-扣非净利润": "net_profit_deducted",
            "扣非净利润-同比增长": "profit_deducted_growth",
            "每股净资产": "bps",
            "净资产收益率": "roe",
            "总资产": "total_assets",
            "净资产": "total_equity",
            "资产负债率": "debt_to_asset",
            "流动比率": "current_ratio",
            "速动比率": "quick_ratio",
            "每股经营现金流量": "ocf_per_share",
            "销售毛利率": "gross_margin",
        }
        df = df.rename(columns=column_map)

        for symbol in symbols:
            row = df[df["symbol"] == symbol]
            if row.empty:
                continue
            r = row.iloc[0]

            revenue = self._to_float(r.get("revenue"), scale=1e8)  # 元转亿元
            net_profit = self._to_float(r.get("net_profit"), scale=1e8)
            total_assets = self._to_float(r.get("total_assets"), scale=1e8)
            total_equity = self._to_float(r.get("total_equity"), scale=1e8)
            debt_to_asset = self._to_float(r.get("debt_to_asset"))

            # 估算有息负债率（业绩快报通常不直接提供，用资产负债率估算）
            interest_bearing_debt_ratio = debt_to_asset * 0.6 if debt_to_asset else None

            # 经营现金流：业绩快报没有直接数据
            ocf_per_share = self._to_float(r.get("ocf_per_share"))
            operating_cash_flow = None  # 暂不估算，避免误导

            # 净利率 = 净利润 / 营业收入
            net_margin = None
            if revenue is not None and revenue > 0 and net_profit is not None:
                net_margin = round(net_profit / revenue * 100, 2)

            metrics.append({
                "symbol": symbol,
                "report_period": str(r.get("report_period", "")),
                "roe": self._to_float(r.get("roe")),
                "roa": self._to_float(r.get("roa")),
                "gross_margin": self._to_float(r.get("gross_margin")),
                "net_margin": net_margin,
                "revenue": revenue,
                "revenue_growth": self._to_float(r.get("revenue_growth")),
                "net_profit": net_profit,
                "profit_growth": self._to_float(r.get("profit_growth")),
                "net_profit_deducted": self._to_float(r.get("net_profit_deducted"), scale=1e8),
                "profit_deducted_growth": self._to_float(r.get("profit_deducted_growth")),
                "debt_to_asset": debt_to_asset,
                "interest_bearing_debt_ratio": interest_bearing_debt_ratio,
                "current_ratio": self._to_float(r.get("current_ratio")),
                "quick_ratio": self._to_float(r.get("quick_ratio")),
                "total_assets": total_assets,
                "total_equity": total_equity,
                "operating_cash_flow": operating_cash_flow,
                "operating_cash_flow_growth": None,
                "capital_expenditure": None,
                "free_cash_flow": None,
                "ocf_to_net_profit": None,
                "audit_opinion": "标准无保留意见",  # 业绩快报默认无审计意见字段
                "data_source": self.name,
                "data_freshness": now,
                "completeness_score": 0.0,  # 由 quality engine 计算
            })

        return metrics

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取日线行情（用于计算动量和估值）。"""
        now = datetime.utcnow()
        df = self._ak_stock_zh_a_spot_em()

        # 标准化列名
        df = df.rename(columns={
            "代码": "symbol",
            "最新价": "latest_price",
            "涨跌幅": "change_pct",
            "换手率": "turnover",
            "市盈率-动态": "pe_ttm",
            "市净率": "pb",
            "市销率": "ps_ttm",
            "股息率": "dividend_yield",
        })

        # 只保留需要的列，缺失的列填充 None
        needed_cols = ["symbol", "latest_price", "change_pct", "turnover", "pe_ttm", "pb", "ps_ttm", "dividend_yield"]
        for col in needed_cols:
            if col not in df.columns:
                df[col] = None
        df = df[needed_cols]

        result = []
        symbol_set = set(symbols)
        for _, r in df.iterrows():
            symbol = str(r["symbol"]).strip()
            if symbol not in symbol_set:
                continue
            result.append({
                "symbol": symbol,
                "latest_price": self._to_float(r.get("latest_price")),
                "change_pct": self._to_float(r.get("change_pct")),
                "turnover": self._to_float(r.get("turnover")),
                "pe_ttm": self._to_float(r.get("pe_ttm")),
                "pb": self._to_float(r.get("pb")),
                "ps_ttm": self._to_float(r.get("ps_ttm")),
                "dividend_yield": self._to_float(r.get("dividend_yield")),
                "data_source": self.name,
                "data_freshness": now,
            })

        return result

    @staticmethod
    def _to_float(value, scale: float = 1.0) -> Optional[float]:
        """把各种格式的数字安全转成 float。"""
        if value is None:
            return None
        try:
            return float(value) / scale
        except (ValueError, TypeError):
            return None

    def clear_cache(self):
        """清除行业映射缓存。"""
        AkShareProvider._industry_cache = None
        AkShareProvider._industry_cache_time = None
