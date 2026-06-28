"""AkShare 数据提供者实现（优化版）。

使用组合接口降低请求次数：
- 股票列表：stock_info_a_code_name
- 行情+估值：stock_zh_a_spot_em（一次性全市场）
- 财务指标：stock_financial_report_sina 或 stock_yjbb_em（业绩快报）
"""
from typing import List, Dict, Any
import pandas as pd
from backend.data.provider import DataProvider


class AkShareProvider(DataProvider):
    """A股数据源：AkShare。"""

    @property
    def name(self) -> str:
        return "akshare"

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取 A股所有股票列表。"""
        import akshare as ak

        df = ak.stock_info_a_code_name()
        result = []
        for _, row in df.iterrows():
            symbol = str(row["code"]).strip()
            name = str(row["name"]).strip()

            if symbol.startswith(("60", "68", "88", "89")):
                market = "SH"
            elif symbol.startswith(("00", "30", "20")):
                market = "SZ"
            elif symbol.startswith(("8", "4")):
                market = "BJ"
            else:
                market = "UNKNOWN"

            result.append({
                "symbol": symbol,
                "name": name,
                "industry": "",
                "sector": "",
                "market": market,
            })

        return result

    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取财务指标。

        使用 stock_yjbb_em（业绩快报）一次性获取全市场最新财报数据。
        """
        import akshare as ak

        metrics = []
        try:
            # 业绩快报，包含最新季度的主要财务指标
            df = ak.stock_yjbb_em(date="20241231")
        except Exception:
            # 如果年底数据未出，尝试最新季度
            try:
                df = ak.stock_yjbb_em(date="20240930")
            except Exception as e:
                print(f"拉取业绩快报失败: {e}")
                return []

        # 标准化列名
        df = df.rename(columns={
            "股票代码": "symbol",
            "股票简称": "name",
            "每股收益": "eps",
            "营业收入-营业收入": "revenue",
            "营业收入-同比增长": "revenue_growth",
            "净利润-净利润": "net_profit",
            "净利润-同比增长": "profit_growth",
            "每股净资产": "bps",
            "净资产收益率": "roe",
            "每股经营现金流量": "ocf_per_share",
            "销售毛利率": "gross_margin",
        })

        for symbol in symbols:
            row = df[df["symbol"] == symbol]
            if row.empty:
                continue
            r = row.iloc[0]
            metrics.append({
                "symbol": symbol,
                "report_period": str(r.get("报告期", "")),
                "roe": self._to_float(r.get("roe")),
                "revenue_growth": self._to_float(r.get("revenue_growth")),
                "profit_growth": self._to_float(r.get("profit_growth")),
                "gross_margin": self._to_float(r.get("gross_margin")),
                "operating_cash_flow": None,  # 业绩快报里没有直接数据
                "audit_opinion": "标准无保留意见",  # 业绩快报默认无审计意见字段
            })

        return metrics

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取日线行情（用于计算动量和估值）。"""
        import akshare as ak

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            print(f"拉取行情失败: {e}")
            return []

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
            })

        return result

    @staticmethod
    def _to_float(value, scale: float = 1.0) -> float:
        """把各种格式的数字安全转成 float。"""
        if value is None:
            return None
        try:
            return float(value) / scale
        except (ValueError, TypeError):
            return None
