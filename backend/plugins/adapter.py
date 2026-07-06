"""把插件信号接入现有过滤与评分引擎的适配器。"""
from typing import Any, Dict, List

from backend.plugins.registry import registry
from backend.plugins.rps import calculate_rps


class PluginAdapter:
    """将 SignalPlugin 的计算结果转换成现有引擎可用的字段。"""

    def __init__(self, enabled_plugins: List[str] = None):
        """enabled_plugins: 启用的插件名列表；None 表示启用所有。"""
        self.enabled = enabled_plugins

    def _filter_enabled(self, results: List[dict]) -> List[dict]:
        if self.enabled is None:
            return results
        return [r for r in results if r["name"] in self.enabled]

    def enrich_metrics(
        self,
        symbol: str,
        metrics: Dict[str, Any],
        ohlcv: List[Dict] = None,
    ) -> Dict[str, Any]:
        """为一只股票运行所有启用的插件，把结果合并到 metrics 中。"""
        results = registry.compute_all(symbol, metrics, ohlcv)
        results = self._filter_enabled(results)

        enriched = dict(metrics)
        plugin_signals = {}
        for r in results:
            plugin_signals[r["name"]] = r
            # 把有 passed 标志的策略/形态作为布尔字段暴露给 filter engine
            if r["passed"] is not None:
                enriched[f"plugin_{r['name']}_passed"] = r["passed"]
            # 把 score 暴露给 scoring engine
            if r["score"] is not None:
                enriched[f"plugin_{r['name']}_score"] = r["score"]

        enriched["_plugin_signals"] = plugin_signals
        return enriched

    def enrich_batch(
        self,
        stocks: List[Dict[str, Any]],
        metrics_map: Dict[str, Dict[str, Any]],
        ohlcv_map: Dict[str, List[Dict]] = None,
        compute_rps: bool = True,
    ) -> Dict[str, Dict[str, Any]]:
        """批量 enrich。"""
        ohlcv_map = ohlcv_map or {}
        out = {}

        # 预计算 RPS 并合并到 metrics
        if compute_rps:
            rps_map = calculate_rps(ohlcv_map, period=120)
            for sym, rps in rps_map.items():
                metrics_map.setdefault(sym, {})["rps_120"] = rps

        for s in stocks:
            sym = s["symbol"]
            out[sym] = self.enrich_metrics(sym, metrics_map.get(sym, {}), ohlcv_map.get(sym))
        return out

    def get_strategy_passed_symbols(
        self,
        stocks: List[Dict[str, Any]],
        enriched_metrics: Dict[str, Dict[str, Any]],
    ) -> Dict[str, List[str]]:
        """汇总每只策略触发了哪些股票。"""
        strategy_names = registry.list_plugins("strategy")
        summary = {name: [] for name in strategy_names}
        for s in stocks:
            sym = s["symbol"]
            m = enriched_metrics.get(sym, {})
            signals = m.get("_plugin_signals", {})
            for name in strategy_names:
                sig = signals.get(name, {})
                if sig.get("passed"):
                    summary[name].append(sym)
        return summary

    def aggregate_technical_score(
        self,
        enriched_metrics: Dict[str, Any],
        weights: Dict[str, float] = None,
    ) -> float:
        """把一只股票的所有插件分数聚合为一个技术面总分。

        默认涵盖 indicator/pattern/strategy/fundamental/sentiment 五类，
        缺失的类型不参与计算。
        """
        signals = enriched_metrics.get("_plugin_signals", {})
        by_type: Dict[str, List[float]] = {}
        for s in signals.values():
            t = s["signal_type"]
            if s["score"] is not None:
                by_type.setdefault(t, []).append(s["score"])

        def _avg(scores):
            return sum(scores) / len(scores) if scores else 0.5

        default_weights = {
            "indicator": 0.35,
            "pattern": 0.20,
            "strategy": 0.20,
            "fundamental": 0.15,
            "sentiment": 0.10,
        }
        weights = weights or default_weights
        total_weight = sum(w for t, w in weights.items() if t in by_type)
        if total_weight == 0:
            return 0.5

        score = sum(_avg(by_type.get(t, [])) * w for t, w in weights.items() if t in by_type) / total_weight
        return round(score, 4)
