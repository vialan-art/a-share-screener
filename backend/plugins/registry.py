"""插件注册表：集中管理所有信号插件。"""
from typing import Dict, List, Type

from backend.plugins.base import BaseSignalPlugin, SignalPlugin


class PluginRegistry:
    """信号插件注册表。"""

    def __init__(self):
        self._plugins: Dict[str, SignalPlugin] = {}

    def register(self, plugin: SignalPlugin) -> SignalPlugin:
        """注册一个插件实例。"""
        self._plugins[plugin.name] = plugin
        return plugin

    def get(self, name: str) -> SignalPlugin:
        return self._plugins[name]

    def list_plugins(self, signal_type: str = None) -> List[str]:
        if signal_type is None:
            return list(self._plugins.keys())
        return [n for n, p in self._plugins.items() if p.signal_type == signal_type]

    def compute_all(
        self,
        symbol: str,
        metrics: dict,
        ohlcv: list = None,
        signal_type: str = None,
    ) -> List[dict]:
        """运行所有（或某类型）插件，返回结果字典列表。"""
        results = []
        for name, plugin in self._plugins.items():
            if signal_type and plugin.signal_type != signal_type:
                continue
            try:
                result = plugin.compute(symbol, metrics, ohlcv)
                results.append({
                    "name": result.name,
                    "signal_type": result.signal_type,
                    "value": result.value,
                    "score": result.score,
                    "passed": result.passed,
                    "reason": result.reason,
                    "meta": result.meta,
                })
            except Exception as e:
                results.append({
                    "name": name,
                    "signal_type": plugin.signal_type,
                    "value": None,
                    "score": None,
                    "passed": None,
                    "reason": f"插件运行失败: {e}",
                    "meta": {},
                })
        return results


# 全局注册表
registry = PluginRegistry()


def register_plugin(plugin_class: Type[BaseSignalPlugin]) -> Type[BaseSignalPlugin]:
    """类装饰器，自动实例化并注册到全局注册表。"""
    registry.register(plugin_class())
    return plugin_class
