"""美股数据源：基于 yfinance。

yfinance 从 Yahoo Finance 获取数据，免费但有限制：
- 股票列表需要预设或从其他来源获取
- 财务数据字段与 A 股不同
- 使用频率过高可能触发限制

本 provider 默认覆盖标普500成分股，可通过 SYMBOL_LIST 环境变量扩展。
"""
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

import pandas as pd
from backend.data.provider import DataProvider


# 默认覆盖标普500前100只，避免请求过多
DEFAULT_US_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B", "UNH", "JNJ",
    "XOM", "JPM", "V", "PG", "HD", "CVX", "MA", "LLY", "ABBV", "PFE",
    "MRK", "PEP", "KO", "BAC", "TMO", "COST", "DIS", "CSCO", "MCD", "WMT",
    "ACN", "DHR", "VZ", "NEE", "ABT", "PM", "NKE", "TXN", "BMY", "QCOM",
    "RTX", "HON", "UPS", "LIN", "AMGN", "SBUX", "MDT", "LOW", "SPGI", "UNP",
    "IBM", "INTU", "AMD", "GS", "LMT", "AXP", "AMAT", "CAT", "GE", "ELV",
    "CVS", "BLK", "T", "DE", "ADBE", "MDLZ", "GILD", "MMC", "SYK", "C",
    "PYPL", "LRCX", "ADI", "CB", "SCHW", "ZTS", "TMUS", "MO", "BKNG", "SO",
    "FI", "PNC", "DUK", "ISRG", "CCI", "EOG", "EW", "ICE", "APD", "CL",
    "ITW", "NSC", "PSA", "TGT", "MCK", "VRTX", "F", "GM", "HUM", "AON",
]


def _get_symbol_list() -> List[str]:
    """读取环境变量或默认列表。"""
    env = os.environ.get("US_SYMBOL_LIST", "")
    if env:
        return [s.strip().upper() for s in env.split(",") if s.strip()]
    return DEFAULT_US_SYMBOLS


class USProvider(DataProvider):
    """美股数据源（yfinance）。"""

    @property
    def name(self) -> str:
        return "us"

    def get_stock_list(self) -> List[Dict[str, Any]]:
        """返回预设美股列表。"""
        result = []
        for symbol in _get_symbol_list():
            result.append({
                "symbol": symbol,
                "name": symbol,
                "industry": "",
                "sector": "",
                "market": "US",
            })
        return result

    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取财务指标。"""
        try:
            import yfinance as yf
        except ImportError:
            print("[USProvider] yfinance 未安装，跳过美股财务数据")
            return []

        metrics = []
        now = datetime.utcnow()

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info or {}
                financials = ticker.financials
                balance = ticker.balance_sheet
                cashflow = ticker.cashflow

                # 获取最新一期数据
                def latest(df: Optional[pd.DataFrame]) -> Optional[pd.Series]:
                    if df is None or df.empty:
                        return None
                    # 列是最新报告期
                    col = df.columns[0]
                    return df[col]

                inc = latest(financials)
                bal = latest(balance)
                cf = latest(cashflow)

                revenue = self._get(inc, "Total Revenue", 1e9)
                net_income = self._get(inc, "Net Income", 1e9)
                total_equity = self._get(bal, "Stockholders Equity", 1e9)
                total_assets = self._get(bal, "Total Assets", 1e9)
                total_debt = self._get(bal, "Total Debt", 1e9)
                operating_cash_flow = self._get(cf, "Operating Cash Flow", 1e9)
                capital_expenditure = self._get(cf, "Capital Expenditure", 1e9)

                net_margin = None
                if revenue and revenue > 0 and net_income is not None:
                    net_margin = round(net_income / revenue * 100, 2)

                roe = None
                if total_equity and total_equity > 0 and net_income is not None:
                    roe = round(net_income / total_equity * 100, 2)

                debt_to_asset = None
                if total_assets and total_assets > 0 and total_debt is not None:
                    debt_to_asset = round(total_debt / total_assets * 100, 2)

                free_cash_flow = None
                if operating_cash_flow is not None and capital_expenditure is not None:
                    free_cash_flow = operating_cash_flow + capital_expenditure  # capex 为负

                metrics.append({
                    "symbol": symbol,
                    "report_period": "",
                    "roe": roe,
                    "roa": None,
                    "gross_margin": info.get("grossMargins", 0) * 100 if info.get("grossMargins") else None,
                    "net_margin": net_margin,
                    "revenue": revenue,
                    "revenue_growth": None,
                    "net_profit": net_income,
                    "profit_growth": None,
                    "net_profit_deducted": None,
                    "profit_deducted_growth": None,
                    "debt_to_asset": debt_to_asset,
                    "interest_bearing_debt_ratio": debt_to_asset,
                    "current_ratio": None,
                    "quick_ratio": None,
                    "total_assets": total_assets,
                    "total_equity": total_equity,
                    "operating_cash_flow": operating_cash_flow,
                    "operating_cash_flow_growth": None,
                    "capital_expenditure": capital_expenditure,
                    "free_cash_flow": free_cash_flow,
                    "ocf_to_net_profit": None,
                    "audit_opinion": "未披露",
                    "data_source": self.name,
                    "data_freshness": now,
                    "completeness_score": 0.0,
                    "pe_ttm": info.get("trailingPE"),
                    "pb": info.get("priceToBook"),
                    "ps_ttm": info.get("priceToSalesTrailing12Months"),
                    "dividend_yield": info.get("dividendYield", 0) * 100 if info.get("dividendYield") else None,
                    "latest_price": info.get("currentPrice") or info.get("regularMarketPrice"),
                    "change_pct": info.get("regularMarketChangePercent"),
                    "turnover": None,
                })
            except Exception as e:
                print(f"[USProvider] {symbol} 获取失败: {e}")
                continue

        return metrics

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """yfinance 的财务指标里已经包含最新价，这里返回空避免重复请求。"""
        return []

    @staticmethod
    def _get(series: Optional[pd.Series], key: str, scale: float = 1.0) -> Optional[float]:
        """安全读取 Series 中的值。"""
        if series is None:
            return None
        if key in series.index:
            try:
                val = float(series[key])
                return val / scale
            except (ValueError, TypeError):
                return None
        return None
