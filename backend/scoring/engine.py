"""多因子评分系统（生产级优化）。

设计思路：
1. 质量、估值、动量三维度分别打分，再加权合成总分。
2. 每个因子内部用百分位排名归一化，避免量纲差异。
3. 增加稳健性处理：异常值截断、空值填充、行业中性化（可选）。
4. 新增增长稳定性因子：营收增长与净利润增长同向且为正时加分。
5. 降低单日涨跌幅噪音，动量主要衡量流动性和趋势一致性。
6. 评分结果附带详细拆解，方便解释。
"""
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    symbol: str
    quality_score: float
    value_score: float
    momentum_score: float
    stability_score: float
    total_score: float
    details: Dict[str, Any] = field(default_factory=dict)


class ScoringEngine:
    """评分引擎。"""

    def __init__(
        self,
        quality_weight: float = 0.40,
        value_weight: float = 0.30,
        momentum_weight: float = 0.10,
        stability_weight: float = 0.10,
        technical_weight: float = 0.10,
        industry_neutral: bool = False,
    ):
        total = quality_weight + value_weight + momentum_weight + stability_weight + technical_weight
        self.quality_weight = quality_weight / total
        self.value_weight = value_weight / total
        self.momentum_weight = momentum_weight / total
        self.stability_weight = stability_weight / total
        self.technical_weight = technical_weight / total
        self.industry_neutral = industry_neutral

    @staticmethod
    def _safe_value(value: Any) -> Optional[float]:
        """安全地把值转成 float，过滤无效值。"""
        if value is None:
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _winsorize(values: List[float], lower_percentile: float = 0.05, upper_percentile: float = 0.95) -> List[float]:
        """对数组进行缩尾处理，减少极端值影响。"""
        clean = sorted([v for v in values if v is not None and not math.isnan(v)])
        if len(clean) < 5:
            return values
        lower = clean[int(len(clean) * lower_percentile)]
        upper = clean[int(len(clean) * upper_percentile)]
        return [min(max(v, lower), upper) if v is not None and not math.isnan(v) else v for v in values]

    @staticmethod
    def _percentile_rank(value: float, values: List[float], higher_is_better: bool = True) -> float:
        """计算某个值在一组值中的百分位排名（稳健版）。"""
        clean_values = sorted([v for v in values if v is not None and not math.isnan(v)])
        if not clean_values:
            return 0.5

        n = len(clean_values)
        below = 0
        for v in clean_values:
            if v <= value:
                below += 1
            else:
                break

        percentile = max(0.0, min(1.0, (below - 0.5) / n))
        return percentile if higher_is_better else 1 - percentile

    def _quality_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> tuple[float, Dict[str, Any]]:
        """质量分：盈利能力 + 成长性 + 现金流健康。"""
        scores = []
        details = {}

        roe = self._safe_value(metrics.get("roe"))
        if roe is not None:
            roe_capped = max(min(roe, 100.0), -50.0)
            score = self._percentile_rank(roe_capped, benchmark.get("roe", []), True)
            scores.append(score)
            details["roe_score"] = round(score, 4)

        gross_margin = self._safe_value(metrics.get("gross_margin"))
        if gross_margin is not None:
            gm_capped = max(min(gross_margin, 100.0), -50.0)
            score = self._percentile_rank(gm_capped, benchmark.get("gross_margin", []), True)
            scores.append(score)
            details["gross_margin_score"] = round(score, 4)

        net_margin = self._safe_value(metrics.get("net_margin"))
        if net_margin is not None:
            nm_capped = max(min(net_margin, 100.0), -100.0)
            score = self._percentile_rank(nm_capped, benchmark.get("net_margin", []), True)
            scores.append(score)
            details["net_margin_score"] = round(score, 4)

        profit_growth = self._safe_value(metrics.get("profit_deducted_growth"))
        growth_key = "profit_deducted_growth"
        if profit_growth is None:
            profit_growth = self._safe_value(metrics.get("profit_growth"))
            growth_key = "profit_growth"
        if profit_growth is not None:
            pg_capped = max(min(profit_growth, 100.0), -50.0)
            score = self._percentile_rank(pg_capped, benchmark.get(growth_key, benchmark.get("profit_growth", [])), True)
            scores.append(score)
            details["growth_score"] = round(score, 4)

        ocf_ratio = self._safe_value(metrics.get("ocf_to_net_profit"))
        if ocf_ratio is not None:
            ratio_capped = max(min(ocf_ratio, 10.0), -5.0)
            score = self._percentile_rank(ratio_capped, benchmark.get("ocf_to_net_profit", []), True)
            scores.append(score)
            details["ocf_ratio_score"] = round(score, 4)

        if not scores:
            return 0.5, details
        return sum(scores) / len(scores), details

    def _value_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> tuple[float, Dict[str, Any]]:
        """估值分：PE/PB 越低越好，股息率越高越好。"""
        scores = []
        details = {}

        pe = self._safe_value(metrics.get("pe_ttm"))
        if pe is not None:
            if pe > 0:
                pe_capped = min(pe, 200.0)
                score = self._percentile_rank(pe_capped, benchmark.get("pe_ttm", []), False)
                scores.append(score)
                details["pe_score"] = round(score, 4)
            else:
                scores.append(0.0)
                details["pe_score"] = 0.0

        pb = self._safe_value(metrics.get("pb"))
        if pb is not None:
            if pb > 0:
                pb_capped = min(pb, 50.0)
                score = self._percentile_rank(pb_capped, benchmark.get("pb", []), False)
                scores.append(score)
                details["pb_score"] = round(score, 4)
            else:
                scores.append(0.0)
                details["pb_score"] = 0.0

        dividend_yield = self._safe_value(metrics.get("dividend_yield"))
        if dividend_yield is not None and dividend_yield >= 0:
            dy_capped = min(dividend_yield, 20.0)
            score = self._percentile_rank(dy_capped, benchmark.get("dividend_yield", []), True)
            scores.append(score)
            details["dividend_score"] = round(score, 4)

        if not scores:
            return 0.5, details
        return sum(scores) / len(scores), details

    def _stability_score(self, metrics: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """增长稳定性分：营收与利润同向增长，现金流能覆盖利润。"""
        details = {}
        checks = []

        revenue_growth = self._safe_value(metrics.get("revenue_growth"))
        profit_growth = self._safe_value(metrics.get("profit_growth"))
        profit_deducted_growth = self._safe_value(metrics.get("profit_deducted_growth"))
        ocf_ratio = self._safe_value(metrics.get("ocf_to_net_profit"))

        if revenue_growth is not None and revenue_growth >= 0:
            checks.append(True)
            details["revenue_growing"] = True
        elif revenue_growth is not None:
            checks.append(False)
            details["revenue_growing"] = False

        if profit_growth is not None and profit_growth >= 0:
            checks.append(True)
            details["profit_growing"] = True
        elif profit_growth is not None:
            checks.append(False)
            details["profit_growing"] = False

        if profit_deducted_growth is not None and profit_deducted_growth >= 0:
            checks.append(True)
            details["profit_deducted_growing"] = True
        elif profit_deducted_growth is not None:
            checks.append(False)
            details["profit_deducted_growing"] = False

        if ocf_ratio is not None and ocf_ratio >= 0.8:
            checks.append(True)
            details["ocf_strong"] = True
        elif ocf_ratio is not None:
            details["ocf_strong"] = False

        if not checks:
            return 0.5, details

        score = sum(checks) / len(checks)
        return score, details

    def _momentum_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> tuple[float, Dict[str, Any]]:
        """动量分：衡量流动性，避免极端换手。"""
        scores = []
        details = {}

        turnover = self._safe_value(metrics.get("turnover"))
        if turnover is not None:
            if turnover > 15.0:
                score = 0.3
            elif turnover < 0.1:
                score = 0.3
            else:
                score = self._percentile_rank(turnover, benchmark.get("turnover", []), True)
            scores.append(score)
            details["turnover_score"] = round(score, 4)

        if not scores:
            return 0.5, details
        return sum(scores) / len(scores), details

    def _technical_score(self, metrics: Dict[str, Any]) -> tuple[float, Dict[str, Any]]:
        """技术面分：聚合所有插件信号（指标/形态/策略/基本面/情绪）。"""
        signals = metrics.get("_plugin_signals", {})
        if not signals:
            return 0.5, {"note": "无插件信号"}

        by_type: Dict[str, List[float]] = {}
        for s in signals.values():
            t = s["signal_type"]
            if s["score"] is not None:
                by_type.setdefault(t, []).append(s["score"])

        def _avg(scores):
            return sum(scores) / len(scores) if scores else 0.5

        # 技术面维度内部权重：指标/形态/策略为主，基本面和情绪插件为辅
        weights = {
            "indicator": 0.35,
            "pattern": 0.20,
            "strategy": 0.20,
            "fundamental": 0.15,
            "sentiment": 0.10,
        }
        total_weight = sum(w for t, w in weights.items() if t in by_type)
        if total_weight == 0:
            return 0.5, {"note": "无可用插件分数"}

        score = sum(_avg(by_type.get(t, [])) * w for t, w in weights.items() if t in by_type) / total_weight
        details = {t: round(_avg(scores), 4) for t, scores in by_type.items()}
        return round(score, 4), details

    def _build_benchmark(self, all_metrics: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """把一组股票的指标收集起来，用于计算百分位，并做缩尾处理。"""
        benchmark = {
            "roe": [],
            "gross_margin": [],
            "net_margin": [],
            "profit_growth": [],
            "profit_deducted_growth": [],
            "ocf_to_net_profit": [],
            "pe_ttm": [],
            "pb": [],
            "dividend_yield": [],
            "turnover": [],
        }

        for m in all_metrics:
            for key in benchmark:
                value = self._safe_value(m.get(key))
                if value is not None:
                    benchmark[key].append(value)

        for key in benchmark:
            benchmark[key] = self._winsorize(benchmark[key])

        return benchmark

    def score_batch(
        self,
        stocks: List[Dict[str, Any]],
        metrics_map: Dict[str, Dict[str, Any]],
    ) -> List[ScoreResult]:
        """对一批股票打分。"""
        all_metrics = list(metrics_map.values())
        benchmark = self._build_benchmark(all_metrics)

        results = []
        for stock in stocks:
            symbol = stock["symbol"]
            metrics = metrics_map.get(symbol, {})

            q, q_details = self._quality_score(metrics, benchmark)
            v, v_details = self._value_score(metrics, benchmark)
            s, s_details = self._stability_score(metrics)
            m_score, m_details = self._momentum_score(metrics, benchmark)
            t_score, t_details = self._technical_score(metrics)

            total = (
                q * self.quality_weight
                + v * self.value_weight
                + s * self.stability_weight
                + m_score * self.momentum_weight
                + t_score * self.technical_weight
            )

            results.append(ScoreResult(
                symbol=symbol,
                quality_score=round(q, 4),
                value_score=round(v, 4),
                momentum_score=round(m_score, 4),
                stability_score=round(s, 4),
                total_score=round(total, 4),
                details={
                    "weights": {
                        "quality": self.quality_weight,
                        "value": self.value_weight,
                        "stability": self.stability_weight,
                        "momentum": self.momentum_weight,
                        "technical": self.technical_weight,
                    },
                    "quality": q_details,
                    "value": v_details,
                    "stability": s_details,
                    "momentum": m_details,
                    "technical": t_details,
                },
            ))

        results.sort(key=lambda x: x.total_score, reverse=True)
        return results
