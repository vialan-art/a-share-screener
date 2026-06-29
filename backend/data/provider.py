"""数据源接口定义。"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class DataProvider(ABC):
    """数据源抽象基类。所有数据源（AkShare/Mock/未来其他）都要实现这三个方法。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """返回数据源名称。"""
        pass

    @abstractmethod
    def get_stock_list(self) -> List[Dict[str, Any]]:
        """获取股票列表。

        返回列表中每个元素应包含：
        - symbol: 股票代码，如 "000001"
        - name: 股票名称
        - industry: 行业（可为空）
        - sector: 板块（可为空）
        - market: 交易所，如 "SH"/"SZ"/"BJ"
        """
        pass

    @abstractmethod
    def get_financial_metrics(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取财务指标。

        返回列表中每个元素应包含尽可能多的字段，关键字段见 quality.engine.CRITICAL_FIELDS。
        """
        pass

    @abstractmethod
    def get_daily_prices(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """获取日线行情和估值数据。"""
        pass
