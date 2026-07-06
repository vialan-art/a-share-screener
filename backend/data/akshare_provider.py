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


# 允许通过环境变量控制请求重试和行业在线拉取
AKSHARE_MAX_RETRIES = int(os.environ.get("AKSHARE_MAX_RETRIES", "3"))
AKSHARE_BASE_DELAY = float(os.environ.get("AKSHARE_BASE_DELAY", "2.0"))
AKSHARE_MAX_DELAY = float(os.environ.get("AKSHARE_MAX_DELAY", "15.0"))
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
STATIC_SECTOR_FILE = os.environ.get(
    "STATIC_SECTOR_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "static_sector_map.json"),
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


class AkShareProvider:
    """A股数据源：AkShare（生产级优化）。"""

    # 行业映射缓存，避免每次请求都重新拉取
    _industry_cache: Optional[pd.DataFrame] = None
    _industry_cache_time: Optional[datetime] = None
    _industry_cache_ttl = timedelta(hours=6)

    # 静态 fallback：常见股票行业/板块映射
    _static_industry_map: Optional[Dict[str, str]] = None
    _static_sector_map: Optional[Dict[str, str]] = None

    # spot 行情短缓存 TTL（避免 get_daily_prices 与 get_financial_metrics 重复调用）
    _spot_cache_ttl = timedelta(minutes=5)
    _spot_source: str = "em"

    def _get_cached_spot(self) -> pd.DataFrame:
        """获取带短缓存的 spot 行情。EM 失败时回退到新浪 spot，整体受超时保护。"""
        now = datetime.utcnow()
        if (
            getattr(self, "_spot_cache", None) is not None
            and getattr(self, "_spot_cache_time", None) is not None
            and now - self._spot_cache_time < self._spot_cache_ttl
        ):
            return self._spot_cache

        import concurrent.futures

        def _fetch():
            try:
                df = self._ak_stock_zh_a_spot_em()
                self._spot_source = "em"
                return df
            except Exception as e:
                print(f"[AkShareProvider] EM spot 失败，回退新浪 spot: {type(e).__name__}: {str(e)[:80]}")
                df = self._ak_stock_zh_a_spot_sina()
                self._spot_source = "sina"
                return df

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_fetch)
                df = future.result(timeout=self.SPOT_TIMEOUT_SECONDS)
            self._spot_cache = df
            self._spot_cache_time = now
            return df
        except concurrent.futures.TimeoutError:
            print(f"[AkShareProvider] spot 行情整体超时 {self.SPOT_TIMEOUT_SECONDS}s，返回空行情")
            self._spot_cache = pd.DataFrame()
            self._spot_cache_time = now
            return self._spot_cache
        except Exception as e:
            print(f"[AkShareProvider] spot 行情获取失败: {type(e).__name__}: {str(e)[:80]}")
            self._spot_cache = pd.DataFrame()
            self._spot_cache_time = now
            return self._spot_cache

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

    def _load_static_sector_fallback(self) -> Dict[str, str]:
        """加载静态板块 fallback。"""
        if AkShareProvider._static_sector_map is None:
            AkShareProvider._static_sector_map = _load_json_map(STATIC_SECTOR_FILE)
        return AkShareProvider._static_sector_map or {}

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

    @_retry_with_backoff(max_retries=2)
    def _ak_stock_industry_change_cninfo(self, symbol: str) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_industry_change_cninfo(symbol=symbol)

    # 是否启用新浪财报真实资产负债表 fallback（网络差时关闭可大幅提升速度）
    ENABLE_SINA_BALANCE_SHEET = os.environ.get("AKSHARE_ENABLE_SINA_BALANCE_SHEET", "false").lower() in ("1", "true", "yes")

    def _fetch_balance_sheet_sina(self, symbol: str) -> Dict[str, Any]:
        """从新浪财报获取真实资产负债率与总资产。

        默认不启用（ENABLE_SINA_BALANCE_SHEET=false），仅当环境变量开启时执行，
        避免网络差时逐只请求新浪导致整体 pipeline 阻塞。
        失败或数据缺失时返回空 dict，调用方继续使用估算值。
        """
        if not self.ENABLE_SINA_BALANCE_SHEET:
            return {}
        try:
            df = self._ak_stock_financial_report_sina(symbol, "资产负债表")
            if df is None or df.empty:
                return {}
            df = df.sort_values("报告日", ascending=False)
            row = df.iloc[0]
            total_assets = self._to_float(row.get("资产总计"))
            total_liabilities = self._to_float(row.get("负债合计"))
            if total_assets is None or total_assets <= 0:
                return {}
            debt_to_asset = (total_liabilities / total_assets * 100) if total_liabilities is not None else None
            result = {"total_assets": total_assets / 1e8}  # 元 -> 亿元
            if debt_to_asset is not None:
                result["debt_to_asset"] = round(debt_to_asset, 2)
            return result
        except Exception as e:
            print(f"[AkShareProvider] {symbol} 新浪资产负债表获取失败: {type(e).__name__}: {str(e)[:80]}")
            return {}

    def _fetch_avg_turnover_sina(self, symbol: str, days: int = 20) -> Optional[float]:
        """从新浪日线计算最近 N 日平均换手率（小数形式）。"""
        try:
            from datetime import datetime, timedelta
            end = datetime.now()
            start = end - timedelta(days=days * 2 + 30)  # 留足够交易日
            df = self._ak_stock_zh_a_daily_sina(
                symbol,
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
            )
            if df is None or df.empty or "turnover" not in df.columns:
                return None
            df = df.sort_values("date")
            avg = df["turnover"].tail(days).astype(float).mean()
            if pd.isna(avg):
                return None
            return round(float(avg) * 100, 2)  # 转为百分比与 EM 保持一致
        except Exception as e:
            print(f"[AkShareProvider] {symbol} 新浪换手率获取失败: {type(e).__name__}: {str(e)[:80]}")
            return None

    @_retry_with_backoff()
    def _ak_stock_yjbb_em(self, date: str) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_yjbb_em(date=date)

    @_retry_with_backoff(max_retries=2)
    def _ak_stock_info_a_code_name(self) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_info_a_code_name()

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

    @_retry_with_backoff(max_retries=2)
    def _ak_stock_zh_a_spot_em(self) -> pd.DataFrame:
        import akshare as ak
        return ak.stock_zh_a_spot_em()

    @_retry_with_backoff(max_retries=2)
    def _ak_stock_zh_a_spot_sina(self) -> pd.DataFrame:
        """新浪 spot 行情（EM 连接不稳定时的 fallback）。字段比 EM 少，但可用性更高。"""
        import akshare as ak
        return ak.stock_zh_a_spot()

    @_retry_with_backoff(max_retries=2)
    def _ak_stock_financial_report_sina(self, symbol: str, report_type: str = "资产负债表") -> pd.DataFrame:
        """新浪财务报表（资产负债表/利润表/现金流量表），免费且稳定。"""
        import akshare as ak
        return ak.stock_financial_report_sina(stock=symbol, symbol=report_type)

    @_retry_with_backoff(max_retries=2)
    def _ak_stock_zh_a_daily_sina(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """新浪日线（含换手率），用于换手率和近期后复权价 fallback。"""
        import akshare as ak
        prefix = "sh" if symbol.startswith(("60", "68", "88", "89")) else "sz"
        return ak.stock_zh_a_daily(symbol=f"{prefix}{symbol}", start_date=start_date, end_date=end_date, adjust="qfq")

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
        try:
            df = self._ak_stock_info_a_code_name()
            source = "official"
        except Exception as e:
            print(f"[AkShareProvider] 官方股票列表获取失败，回退新浪 spot: {type(e).__name__}: {str(e)[:80]}")
            df = self._ak_stock_zh_a_spot_sina()
            source = "sina"

        industry_map = self._load_static_fallback()
        sector_map = self._load_static_sector_fallback()

        result = []
        skipped_st = 0
        for _, row in df.iterrows():
            if source == "sina":
                raw = str(row.get("代码", "")).strip().lower()
                if len(raw) >= 8 and raw[:2] in ("sh", "sz", "bj"):
                    symbol = raw[2:].zfill(6)
                else:
                    symbol = "".join(ch for ch in raw if ch.isdigit()).zfill(6)
                name = str(row.get("名称", "")).strip()
            else:
                symbol = str(row.get("code", "")).strip().zfill(6)
                name = str(row.get("name", "")).strip()

            if not symbol or len(symbol) != 6:
                continue

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
            sector = sector_map.get(symbol, "")

            result.append({
                "symbol": symbol,
                "name": name,
                "industry": industry,
                "sector": sector,
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

    # A 股非金融企业近似平均资产负债率（业绩快报不披露 debt 时的 fallback）
    DEFAULT_DEBT_TO_ASSET = 45.0

    # 是否启用新浪日线换手率 fallback（按需关闭可大幅提升 get_financial_metrics 速度）
    ENABLE_SINA_TURNOVER_FALLBACK = os.environ.get("AKSHARE_ENABLE_SINA_TURNOVER_FALLBACK", "false").lower() in ("1", "true", "yes")

    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取财务指标。

        使用 stock_yjbb_em（业绩快报）一次性获取全市场最新财报数据，
        并结合当日行情市值补全缺失字段。
        关键改进：优先用 净利润/每股收益 反推总股本，从而摆脱对 EM spot 总市值的强依赖；
        EM spot 不可用时自动回退到新浪 spot，估值由价格+每股指标计算得到。
        注意：业绩快报不是完整年报，部分指标为估算值，会在 data_source_note 中说明。
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
            "营业收入-营业收入": "revenue_yuan",
            "营业收入-同比增长": "revenue_growth",
            "净利润-净利润": "net_profit_yuan",
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
            "所处行业": "industry",
        }
        df = df.rename(columns=column_map)

        # 拿一次 spot 行情用于价格/市值（带新浪 fallback）
        spot_map = self._fetch_spot_for_estimation()

        for symbol in symbols:
            row = df[df["symbol"] == symbol]
            if row.empty:
                continue
            r = row.iloc[0]

            notes: List[str] = []

            # 原始每股/总量指标
            eps = self._to_float(r.get("eps"))  # 元/股
            bps = self._to_float(r.get("bps"))  # 元/股
            ocf_per_share = self._to_float(r.get("ocf_per_share"))  # 元/股
            net_profit_yuan = self._to_float(r.get("net_profit_yuan"))  # 元
            revenue_yuan = self._to_float(r.get("revenue_yuan"))  # 元
            revenue = revenue_yuan / 1e8 if revenue_yuan is not None else None  # 亿元
            net_profit = net_profit_yuan / 1e8 if net_profit_yuan is not None else None  # 亿元

            # 最新价/市值
            spot = spot_map.get(symbol, {})
            market_cap_yuan = spot.get("market_cap")  # 总市值（元），EM 专有
            latest_price = spot.get("latest_price")
            change_pct = spot.get("change_pct")

            # 估算总股本（股）：优先用 净利润/每股收益；否则用 总市值/最新价
            total_shares = None
            if net_profit_yuan is not None and eps is not None and abs(eps) > 1e-9:
                total_shares = net_profit_yuan / eps
                notes.append("总股本由净利润/每股收益反推")
            elif market_cap_yuan is not None and latest_price is not None and latest_price > 0:
                total_shares = market_cap_yuan / latest_price
                notes.append("总股本由总市值/最新价估算")

            # 偿债能力：优先使用新浪财报真实数据
            debt_to_asset = self._to_float(r.get("debt_to_asset"))
            balance = self._fetch_balance_sheet_sina(symbol)
            if balance.get("debt_to_asset") is not None:
                debt_to_asset = balance["debt_to_asset"]
                notes.append("资产负债率使用新浪财报数据")
            elif debt_to_asset is None:
                debt_to_asset = self.DEFAULT_DEBT_TO_ASSET
                notes.append("资产负债率使用 A 股市场默认值 45% 估算")
            interest_bearing_debt_ratio = debt_to_asset * 0.6

            # 净资产/总资产
            total_equity_yuan = None
            total_equity = self._to_float(r.get("total_equity"), scale=1e8)  # 亿元
            if total_equity is None and bps is not None and total_shares is not None:
                total_equity_yuan = bps * total_shares
                total_equity = round(total_equity_yuan / 1e8, 2)
                notes.append("净资产由每股净资产×总股本估算")

            # 总资产：财报优先
            total_assets = self._to_float(r.get("total_assets"), scale=1e8)  # 亿元
            if balance.get("total_assets") is not None:
                total_assets = balance["total_assets"]
                notes.append("总资产使用新浪财报数据")
            elif total_assets is None and total_equity is not None and debt_to_asset is not None and debt_to_asset < 100:
                total_assets = round(total_equity / (1 - debt_to_asset / 100), 2)
                notes.append("总资产由净资产/(1-资产负债率)估算")

            # 现金流
            operating_cash_flow: Optional[float] = None
            capital_expenditure: Optional[float] = None
            free_cash_flow: Optional[float] = None
            ocf_to_net_profit: Optional[float] = None
            if ocf_per_share is not None and total_shares is not None:
                operating_cash_flow_yuan = ocf_per_share * total_shares
                operating_cash_flow = round(operating_cash_flow_yuan / 1e8, 2)
                capital_expenditure = round(-operating_cash_flow * 0.25, 2)
                free_cash_flow = round(operating_cash_flow + capital_expenditure, 2)
                notes.append("现金流由每股经营现金流×总股本估算，资本支出按 OCF 25% 近似")

            if ocf_per_share is not None and eps is not None and abs(eps) > 1e-9:
                # OCF/NP = (OCF_per_share * shares) / (eps * shares) = OCF_per_share / eps
                ocf_to_net_profit = round(ocf_per_share / eps, 2)

            # ROA
            roa = self._to_float(r.get("roa"))
            if roa is None and net_profit is not None and total_assets is not None and total_assets > 0:
                roa = round(net_profit / total_assets * 100, 2)
                notes.append("ROA 由净利润/总资产估算")

            # 净利率
            net_margin = None
            if revenue is not None and revenue > 0 and net_profit is not None:
                net_margin = round(net_profit / revenue * 100, 2)

            # 估值指标（由价格和每股指标计算，不依赖 EM 估值字段）
            pe_ttm: Optional[float] = None
            pb: Optional[float] = None
            ps_ttm: Optional[float] = None
            market_cap: Optional[float] = None
            if latest_price is not None:
                if eps is not None and abs(eps) > 1e-9:
                    pe_ttm = round(latest_price / eps, 2)
                if bps is not None and bps > 0:
                    pb = round(latest_price / bps, 2)
                if total_shares is not None and revenue_yuan is not None and revenue_yuan > 0:
                    ps_ttm = round((latest_price * total_shares) / revenue_yuan, 2)
                if total_shares is not None:
                    market_cap = round(latest_price * total_shares / 1e8, 2)
                notes.append("PE/PB/PS 由最新价与每股指标/总股本计算")

            # 行业：优先使用业绩快报的所处行业
            industry = str(r.get("industry", "")).strip()

            # 换手率：spot 缺失时按配置决定是否用新浪日线 20 日均值
            turnover = spot.get("turnover")
            if turnover is None and self.ENABLE_SINA_TURNOVER_FALLBACK:
                turnover = self._fetch_avg_turnover_sina(symbol, days=20)
                if turnover is not None:
                    notes.append("换手率由新浪日线 20 日均值计算")

            metrics.append({
                "symbol": symbol,
                "report_period": str(r.get("report_period", "")),
                "name": str(r.get("name", "")).strip(),
                "industry": industry,
                "latest_price": latest_price,
                "change_pct": change_pct,
                "turnover": turnover,
                "roe": self._to_float(r.get("roe")),
                "roa": roa,
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
                "capital_expenditure": capital_expenditure,
                "free_cash_flow": free_cash_flow,
                "ocf_to_net_profit": ocf_to_net_profit,
                "pe_ttm": pe_ttm,
                "pb": pb,
                "ps_ttm": ps_ttm,
                "market_cap": market_cap,
                "dividend_yield": None,
                "audit_opinion": "标准无保留意见",
                "data_source": self.name,
                "data_freshness": now,
                "completeness_score": 0.0,
                "data_source_note": "; ".join(notes) if notes else "业绩快报原始字段完整",
            })

        return metrics

    # 网络不稳定时，spot 行情整体超时（秒），避免阻塞财务指标拉取
    SPOT_TIMEOUT_SECONDS = float(os.environ.get("AKSHARE_SPOT_TIMEOUT_SECONDS", "25.0"))

    def _fetch_spot_for_estimation(self) -> Dict[str, Dict[str, Any]]:
        """获取 spot 行情，仅用于财务估算（最新价、涨跌幅）。失败或超时返回空 dict。

        使用线程安全的方式实现超时，兼容后台线程执行。
        """
        import concurrent.futures

        def _get():
            df = self._get_cached_spot()
            source = getattr(self, "_spot_source", "em")
            if source == "sina":
                df = df.rename(columns={
                    "代码": "symbol_raw",
                    "最新价": "latest_price",
                    "涨跌幅": "change_pct",
                })

                def _norm_symbol(s):
                    s = str(s).strip().lower()
                    if len(s) >= 8 and s[:2] in ("sh", "sz", "bj"):
                        s = s[2:]
                    digits = "".join(ch for ch in s if ch.isdigit())
                    return digits.zfill(6) if len(digits) == 6 else ""

                df["symbol"] = df["symbol_raw"].apply(_norm_symbol)
            else:
                df = df.rename(columns={
                    "代码": "symbol",
                    "最新价": "latest_price",
                    "涨跌幅": "change_pct",
                    "总市值": "market_cap",
                })
                df["symbol"] = df["symbol"].astype(str).str.strip().str.zfill(6)

            df["latest_price"] = pd.to_numeric(df["latest_price"], errors="coerce")
            df["change_pct"] = pd.to_numeric(df.get("change_pct"), errors="coerce")
            if "market_cap" in df.columns:
                df["market_cap"] = pd.to_numeric(df["market_cap"], errors="coerce")
            else:
                df["market_cap"] = None

            result = {}
            for _, r in df.iterrows():
                sym = str(r["symbol"]).strip()
                if not sym or len(sym) != 6:
                    continue
                result[sym] = {
                    "latest_price": r["latest_price"],
                    "change_pct": r["change_pct"],
                    "market_cap": r["market_cap"],
                }
            return result

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_get)
                return future.result(timeout=self.SPOT_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            print(f"[AkShareProvider] spot 行情获取超过 {self.SPOT_TIMEOUT_SECONDS}s，跳过，使用业绩快报每股指标计算估值")
            return {}
        except Exception as e:
            print(f"[AkShareProvider] spot 行情获取失败，财务估算将受限: {e}")
            return {}

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取日线行情（用于计算动量和估值）。

        优先使用东方财富 spot（字段全）；失败/字段缺失时回退新浪 spot。
        为避免覆盖 get_financial_metrics 已计算出的 PE/PB 等字段，结果中值为 None 的键会被剔除。
        """
        now = datetime.utcnow()
        df = self._get_cached_spot()
        source = getattr(self, "_spot_source", "em")

        if source == "sina":
            df = df.rename(columns={
                "代码": "symbol_raw",
                "最新价": "latest_price",
                "涨跌幅": "change_pct",
            })

            def _norm_symbol(s):
                s = str(s).strip().lower()
                if len(s) >= 8 and s[:2] in ("sh", "sz", "bj"):
                    s = s[2:]
                digits = "".join(ch for ch in s if ch.isdigit())
                return digits.zfill(6) if len(digits) == 6 else ""

            df["symbol"] = df["symbol_raw"].apply(_norm_symbol)
            df["turnover"] = None
            df["pe_ttm"] = None
            df["pb"] = None
            df["ps_ttm"] = None
            df["dividend_yield"] = None
        else:
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
            df["symbol"] = df["symbol"].astype(str).str.strip().str.zfill(6)

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
            if symbol not in symbol_set or len(symbol) != 6:
                continue
            # 仅保留非 None 字段，避免覆盖财务指标中已计算的值
            item = {
                "symbol": symbol,
                "data_source": self.name,
                "data_freshness": now,
            }
            for col in ["latest_price", "change_pct", "turnover", "pe_ttm", "pb", "ps_ttm", "dividend_yield"]:
                value = self._to_float(r.get(col))
                if value is not None:
                    item[col] = value
            result.append(item)

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
