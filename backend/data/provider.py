"""可插拔数据源接口。

核心思想：
不管数据源是 AkShare、Tushare、yfinance 还是以后的付费 API，
对上层（过滤、评分）暴露的接口都是一样的。

这就叫 "抽象接口" 或 "数据提供者模式"。
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DataProvider(ABC):
    """数据源抽象基类。"""

    @abstractmethod
    def get_stock_list(self) -> List[Dict[str, Any]]:
        """返回股票列表。

        每个元素应该包含：
        {
            "symbol": "000001",
            "name": "平安银行",
            "industry": "银行",
            "sector": "金融",
            "market": "SZ"
        }
        """
        pass

    @abstractmethod
    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """返回财务指标。"""
        pass

    @abstractmethod
    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """返回日线行情（用于计算动量）。"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """数据源名称。"""
        pass
