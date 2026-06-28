"""数据源工厂。"""
from backend.data.provider import DataProvider
from backend.data.akshare_provider import AkShareProvider


# 把数据源名称映射到具体实现
PROVIDERS = {
    "akshare": AkShareProvider,
    # 以后可以在这里加：tushare、yfinance、bloomberg 等
}


def get_provider(name: str = "akshare") -> DataProvider:
    """根据名称创建对应的数据源实例。"""
    if name not in PROVIDERS:
        raise ValueError(f"未知数据源: {name}，可选：{list(PROVIDERS.keys())}")
    return PROVIDERS[name]()
