"""模拟数据源（用于本地开发和测试）。

当 AkShare 网络不稳定或本地想快速验证前端时，可以用这个 provider。
它生成看起来像真实 A 股的数据。

重要：为了保证结果可复现、可调试，MockProvider 使用确定性算法：
同一只股票代码每次生成的名称、行业、财务指标都相同。
"""
import hashlib
from datetime import datetime
from typing import List, Dict, Any
from backend.data.provider import DataProvider


class MockProvider(DataProvider):
    """模拟 A 股数据源。"""

    INDUSTRIES = [
        "银行", "白酒", "医药生物", "电力", "煤炭", "食品饮料",
        "电子", "汽车", "房地产", "化工", "机械", "计算机",
    ]

    NAMES = [
        "平安", "华夏", "招商", "茅台", "五粮液", "恒瑞", "迈瑞", "长江",
        "中国神华", "伊利", "海天", "立讯", "比亚迪", "万科", "万华",
        "三一", "科大讯飞", "海康", "隆基", "宁德时代",
    ]

    PREFIXES = ["600", "601", "000", "002", "300"]

    @property
    def name(self) -> str:
        return "mock"

    def _hash(self, seed: str, max_val: int) -> int:
        """基于字符串生成 0 ~ max_val-1 的确定性整数。"""
        digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
        return int(digest, 16) % max_val

    def _uniform(self, seed: str, low: float, high: float) -> float:
        """基于字符串生成 [low, high] 的确定性浮点数。"""
        digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
        return low + (int(digest, 16) % 1000000 / 1000000) * (high - low)

    def _symbol_to_stock(self, symbol: str) -> Dict[str, Any]:
        """把代码映射为确定性股票信息。"""
        name = (
            self.NAMES[self._hash(f"{symbol}:name", len(self.NAMES))]
            + ["股份", "科技", "银行", "能源", "医药", ""][self._hash(f"{symbol}:suffix", 6)]
        )
        industry = self.INDUSTRIES[self._hash(f"{symbol}:industry", len(self.INDUSTRIES))]
        market = "SH" if symbol.startswith("6") else "SZ"
        return {
            "symbol": symbol,
            "name": name,
            "industry": industry,
            "sector": "",
            "market": market,
        }

    def get_stock_list(self) -> List[Dict[str, Any]]:
        # 生成 300 个确定性代码，并按代码排序保证顺序稳定
        symbols = []
        for i in range(300):
            prefix = self.PREFIXES[self._hash(f"stock:{i}:prefix", len(self.PREFIXES))]
            number = 100 + self._hash(f"stock:{i}:number", 900)
            symbols.append(f"{prefix}{number:03d}")
        # 去重并排序
        symbols = sorted(set(symbols))
        return [self._symbol_to_stock(s) for s in symbols]

    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        metrics = []
        for s in symbols:
            revenue = round(self._uniform(f"{s}:revenue", 1.0, 5000.0), 2)
            net_profit = round(revenue * self._uniform(f"{s}:npm", 0.02, 0.25), 2)
            net_profit_deducted = round(net_profit * self._uniform(f"{s}:deduct", 0.75, 1.05), 2)
            ocf = round(net_profit * self._uniform(f"{s}:ocf_ratio", 0.6, 1.4), 2)
            capex = round(-abs(net_profit * self._uniform(f"{s}:capex", 0.1, 0.6)), 2)
            total_assets = round(revenue * self._uniform(f"{s}:asset_turn", 0.5, 3.0), 2)
            total_equity = round(total_assets * self._uniform(f"{s}:equity_ratio", 0.2, 0.7), 2)
            debt = total_assets - total_equity
            interest_bearing = debt * self._uniform(f"{s}:ibd_ratio", 0.3, 0.9)

            metrics.append({
                "symbol": s,
                "report_period": "2024-09-30",
                "roe": round(self._uniform(f"{s}:roe", 2.0, 25.0), 2),
                "roa": round(self._uniform(f"{s}:roa", 1.0, 15.0), 2),
                "gross_margin": round(self._uniform(f"{s}:gross_margin", 10.0, 80.0), 2),
                "net_margin": round(self._uniform(f"{s}:net_margin", 2.0, 30.0), 2),
                "revenue": revenue,
                "revenue_growth": round(self._uniform(f"{s}:revenue_growth", -20.0, 60.0), 2),
                "net_profit": net_profit,
                "profit_growth": round(self._uniform(f"{s}:profit_growth", -30.0, 80.0), 2),
                "net_profit_deducted": net_profit_deducted,
                "profit_deducted_growth": round(self._uniform(f"{s}:profit_deducted_growth", -35.0, 75.0), 2),
                "debt_to_asset": round(debt / total_assets * 100, 2),
                "interest_bearing_debt_ratio": round(interest_bearing / total_assets * 100, 2),
                "current_ratio": round(self._uniform(f"{s}:current_ratio", 0.8, 3.0), 2),
                "quick_ratio": round(self._uniform(f"{s}:quick_ratio", 0.6, 2.5), 2),
                "total_assets": total_assets,
                "total_equity": total_equity,
                "operating_cash_flow": ocf,
                "operating_cash_flow_growth": round(self._uniform(f"{s}:ocf_growth", -40.0, 100.0), 2),
                "capital_expenditure": capex,
                "free_cash_flow": round(ocf + capex, 2),
                "ocf_to_net_profit": round(ocf / net_profit if net_profit else 0, 2),
                "audit_opinion": "标准无保留意见" if self._hash(f"{s}:audit", 100) >= 5 else "保留意见",
                "data_source": self.name,
                "data_freshness": now,
                "completeness_score": 1.0,
            })
        return metrics

    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        return [
            {
                "symbol": s,
                "latest_price": round(self._uniform(f"{s}:price", 5.0, 500.0), 2),
                "change_pct": round(self._uniform(f"{s}:change", -10.0, 10.0), 2),
                "turnover": round(self._uniform(f"{s}:turnover", 0.5, 15.0), 2),
                "pe_ttm": round(self._uniform(f"{s}:pe", 5.0, 80.0), 2) if self._hash(f"{s}:pe_valid", 100) >= 10 else -5.0,
                "pb": round(self._uniform(f"{s}:pb", 0.5, 15.0), 2),
                "ps_ttm": round(self._uniform(f"{s}:ps", 1.0, 20.0), 2),
                "dividend_yield": round(self._uniform(f"{s}:div", 0.0, 6.0), 2),
                "data_source": self.name,
                "data_freshness": now,
            }
            for s in symbols
        ]
