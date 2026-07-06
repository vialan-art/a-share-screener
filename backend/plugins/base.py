"""插件基类与类型定义。

设计目标：让外部量化库（KHunter / InStock 等）的计算逻辑以统一方式接入现有 pipeline，
但不引入它们沉重的 web 层、数据层或自动交易模块。
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Protocol


@dataclass
class SignalResult:
    """单个信号/因子输出。"""
    symbol: str
    name: str
    signal_type: str  # indicator / pattern / strategy / risk
    value: Any  # 原始值：数值、布尔、字符串等
    score: Optional[float] = None  # 归一化到 0-1 的分数，供打分引擎使用
    passed: Optional[bool] = None  # 是否通过过滤/触发条件
    reason: Optional[str] = None  # 人类可读说明
    meta: Dict[str, Any] = None  # 额外细节

    def __post_init__(self):
        if self.meta is None:
            self.meta = {}
        if self.passed is not None:
            self.passed = bool(self.passed)
        if self.score is not None:
            self.score = float(self.score)


class SignalPlugin(Protocol):
    """信号插件协议。所有具体插件只需实现这两个方法即可接入。"""

    @property
    def name(self) -> str:
        ...

    @property
    def signal_type(self) -> str:
        ...

    def compute(
        self,
        symbol: str,
        metrics: Dict[str, Any],
        ohlcv: Optional[List[Dict[str, Any]]] = None,
    ) -> SignalResult:
        ...


class BaseSignalPlugin(ABC):
    """可选的抽象基类，提供通用辅助方法。"""

    name: str = ""
    signal_type: str = ""

    @abstractmethod
    def compute(
        self,
        symbol: str,
        metrics: Dict[str, Any],
        ohlcv: Optional[List[Dict[str, Any]]] = None,
    ) -> SignalResult:
        raise NotImplementedError

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        if value is None:
            return None
        try:
            v = float(value)
            import math
            if math.isnan(v) or math.isinf(v):
                return None
            return v
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ohlcv_to_df(ohlcv: Optional[List[Dict[str, Any]]]) -> Optional["pd.DataFrame"]:
        if not ohlcv:
            return None
        import pandas as pd
        df = pd.DataFrame(ohlcv)
        if df.empty or "close" not in df.columns:
            return None
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        return df
