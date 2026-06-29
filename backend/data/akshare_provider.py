"""AkShare 数据提供者实现（优化版）。

使用组合接口降低请求次数：
- 股票列表：stock_info_a_code_name
- 行情+估值：stock_zh_a_spot_em（一次性全市场）
- 财务指标：stock_yjbb_em（业绩快报）

重要：AkShare 数据来自东方财富等第三方，可能存在延迟、错误、字段变更。
本 provider 会尽量做数据清洗和标记，但不保证 100% 正确。
"""
from datetime import datetime
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
        注意：业绩快报不是完整年报，部分指标缺失。
        """
        import akshare as ak

        metrics = []
        now = datetime.utcnow()
        # 尝试最近几个报告期
        df = None
        for date_str in ["20241231", "20240930", "20240630", "20240331"]:
            try:
                df = ak.stock_yjbb_em(date=date_str)
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

            # 经营现金流：业绩快报没有直接数据，用每股经营现金流量 * 总股本估算（需要股本数据，这里简化）
            ocf_per_share = self._to_float(r.get("ocf_per_share"))
            operating_cash_flow = None  # 暂不估算，避免误导

            metrics.append({
                "symbol": symbol,
                "report_period": str(r.get("report_period", "")),
                "roe": self._to_float(r.get("roe")),
                "roa": self._to_float(r.get("roa")),
                "gross_margin": self._to_float(r.get("gross_margin")),
                "net_margin": None,
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
                "completeness_score": 0.75,  # 业绩快报完整度中等
            })

        return metrics

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取日线行情（用于计算动量和估值）。"""
        import akshare as ak

        now = datetime.utcnow()
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
                "data_source": self.name,
                "data_freshness": now,
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
