"""插件包入口，自动加载所有内置插件。"""
from backend.plugins import base, registry, adapter
from backend.plugins import indicators, patterns, strategies, sequoia_strategies, stock_scanner

__all__ = ["registry", "adapter", "base"]
