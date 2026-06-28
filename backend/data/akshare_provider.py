"""AkShare 数据提供者实现。

AkShare 是一个免费的中文财经数据接口库，
底层爬取的是东方财富、新浪财经等公开数据。
"""
from typing import List, Dict, Any
import time
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

        # stock_info_a_code_name 返回：代码、名称
        df = ak.stock_info_a_code_name()

        # 补充行业信息：用 stock_industry_cninfo 获取
        try:
            industry_df = ak.stock_industry_cninfo()
        except Exception:
            industry_df = pd.DataFrame()

        result = []
        for _, row in df.iterrows():
            symbol = str(row["code"]).strip()
            name = str(row["name"]).strip()

            # 根据代码判断交易所
            if symbol.startswith(("60", "68", "88", "89")):
                market = "SH"
            elif symbol.startswith(("00", "30", "20")):
                market = "SZ"
            elif symbol.startswith(("8", "4")):
                market = "BJ"
            else:
                market = "UNKNOWN"

            # 查找行业
            industry = ""
            if not industry_df.empty:
                match = industry_df[industry_df["股票代码"] == symbol]
                if not match.empty:
                    industry = str(match.iloc[0].get("行业", ""))

            result.append({
                "symbol": symbol,
                "name": name,
                "industry": industry or "未知",
                "sector": "",
                "market": market,
            })

            # 小额限速，避免请求太快被封
            time.sleep(0.02)

        return result

    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取财务指标。

        这里用 AkShare 的财务指标接口批量拉取。
        为了演示和避免被限流，先拉取一个汇总表。
        """
        import akshare as ak

        metrics = []

        # 主要财务指标
        try:
            fin_df = ak.stock_financial_analysis_indicator(symbol="all")
            # 这个接口返回的是所有股票最新一期数据
        except Exception as e:
            print(f"拉取财务指标失败: {e}")
            return []

        for symbol in symbols:
            row = fin_df[fin_df["股票代码"] == symbol]
            if row.empty:
                continue

            r = row.iloc[0]
            metrics.append({
                "symbol": symbol,
                "report_period": str(r.get("报告期", "")),
                "roe": self._to_float(r.get("净资产收益率")),
                "roa": self._to_float(r.get("总资产净利率")),
                "gross_margin": self._to_float(r.get("销售毛利率")),
                "net_margin": self._to_float(r.get("销售净利率")),
                "revenue_growth": self._to_float(r.get("营业收入同比增长率")),
                "profit_growth": self._to_float(r.get("净利润同比增长率")),
                "debt_to_asset": self._to_float(r.get("资产负债率")),
                "current_ratio": self._to_float(r.get("流动比率")),
                "operating_cash_flow": self._to_float(r.get("经营活动现金流量净额"), scale=1e8),
                "audit_opinion": str(r.get("审计意见", "")),
            })

        return metrics

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取日线行情。

        对 MVP 来说，全部股票实时拉取比较慢，
        所以这里用一个汇总行情接口。
        """
        import akshare as ak

        try:
            df = ak.stock_zh_a_spot_em()
        except Exception as e:
            print(f"拉取行情失败: {e}")
            return []

        result = []
        for symbol in symbols:
            row = df[df["代码"] == symbol]
            if row.empty:
                continue
            r = row.iloc[0]
            result.append({
                "symbol": symbol,
                "latest_price": self._to_float(r.get("最新价")),
                "change_pct": self._to_float(r.get("涨跌幅")),
                "turnover": self._to_float(r.get("换手率")),
                "pe_ttm": self._to_float(r.get("市盈率-动态")),
                "pb": self._to_float(r.get("市净率")),
                "ps_ttm": self._to_float(r.get("市销率")),
                "dividend_yield": self._to_float(r.get("股息率")),
            })

        return result

    @staticmethod
    def _to_float(value, scale: float = 1.0) -> float:
        """把各种格式的数字安全转成 float，失败返回 None。"""
        if value is None:
            return None
        try:
            return float(value) / scale
        except (ValueError, TypeError):
            return None
