"""多因子评分系统。

设计思路：
把质量、估值、动量三个维度分别打分，再加权合成总分。
每个因子内部用 Z-score 或分位数归一化，避免不同指标量纲不同的问题。
"""
import math
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class ScoreResult:
    symbol: str
    quality_score: float
    value_score: float
    momentum_score: float
    total_score: float
    details: Dict[str, Any]


class ScoringEngine:
    """评分引擎。"""

    def __init__(
        self,
        quality_weight: float = 0.45,
        value_weight: float = 0.35,
        momentum_weight: float = 0.20,
    ):
        # 权重之和应该等于 1
        total = quality_weight + value_weight + momentum_weight
        self.quality_weight = quality_weight / total
        self.value_weight = value_weight / total
        self.momentum_weight = momentum_weight / total

    def _percentile_rank(self, value: float, values: List[float], higher_is_better: bool = True) -> float:
        """计算某个值在一组值中的百分位排名。

        比如 value 是 50，values 是 [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]，
        那么 50 超过了 40% 的值，百分位就是 0.4（或 0.6，取决于方向）。

        higher_is_better=True：值越大越好（如 ROE）
        higher_is_better=False：值越小越好（如 PE）
        """
        clean_values = [v for v in values if v is not None and not math.isnan(v)]
        if not clean_values:
            return 0.5

        n = len(clean_values)
        # 计算小于等于 value 的比例
        below = sum(1 for v in clean_values if v <= value)
        percentile = below / n

        if higher_is_better:
            return percentile
        else:
            return 1 - percentile

    def _quality_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> float:
        """质量分：盈利能力 + 成长性 + 现金流健康。"""
        scores = []

        # ROE：越高越好
        if metrics.get("roe") is not None:
            scores.append(self._percentile_rank(metrics["roe"], benchmark.get("roe", []), True))

        # 毛利率：越高越好
        if metrics.get("gross_margin") is not None:
            scores.append(self._percentile_rank(metrics["gross_margin"], benchmark.get("gross_margin", []), True))

        # 净利率：越高越好
        if metrics.get("net_margin") is not None:
            scores.append(self._percentile_rank(metrics["net_margin"], benchmark.get("net_margin", []), True))

        # 营收增长：越高越好，但要有上限避免极端
        if metrics.get("revenue_growth") is not None:
            rg = max(min(metrics["revenue_growth"], 100.0), -50.0)
            scores.append(self._percentile_rank(rg, benchmark.get("revenue_growth", []), True))

        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    def _value_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> float:
        """估值分：PE/PB 越低越好，股息率越高越好。"""
        scores = []

        # PE：越低越好，但要大于 0（亏损公司 PE 为负，直接给 0 分）
        pe = metrics.get("pe_ttm")
        if pe is not None and pe > 0:
            scores.append(self._percentile_rank(pe, benchmark.get("pe_ttm", []), False))
        elif pe is not None and pe <= 0:
            scores.append(0.0)

        # PB：越低越好
        pb = metrics.get("pb")
        if pb is not None and pb > 0:
            scores.append(self._percentile_rank(pb, benchmark.get("pb", []), False))
        elif pb is not None and pb <= 0:
            scores.append(0.0)

        # 股息率：越高越好
        if metrics.get("dividend_yield") is not None:
            scores.append(self._percentile_rank(metrics["dividend_yield"], benchmark.get("dividend_yield", []), True))

        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    def _momentum_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> float:
        """动量分：近期涨跌幅 + 换手率。"""
        scores = []

        # 涨跌幅：适中偏好。这里简单处理，涨的比跌的好
        if metrics.get("change_pct") is not None:
            cp = max(min(metrics["change_pct"], 20.0), -20.0)
            scores.append(self._percentile_rank(cp, benchmark.get("change_pct", []), True))

        # 换手率：适中，太高或太低都不好
        turnover = metrics.get("turnover")
        if turnover is not None:
            if turnover > 15.0:  # 换手率过高，投机性强
                scores.append(0.3)
            elif turnover < 0.1:  # 几乎没流动性
                scores.append(0.3)
            else:
                scores.append(self._percentile_rank(turnover, benchmark.get("turnover", []), True))

        if not scores:
            return 0.5
        return sum(scores) / len(scores)

    def _build_benchmark(self, all_metrics: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        """把一组股票的指标收集起来，用于计算百分位。"""
        benchmark = {
            "roe": [],
            "gross_margin": [],
            "net_margin": [],
            "revenue_growth": [],
            "pe_ttm": [],
            "pb": [],
            "dividend_yield": [],
            "change_pct": [],
            "turnover": [],
        }

        for m in all_metrics:
            for key in benchmark:
                value = m.get(key)
                if value is not None and not math.isnan(value):
                    benchmark[key].append(value)

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

            q = self._quality_score(metrics, benchmark)
            v = self._value_score(metrics, benchmark)
            m_score = self._momentum_score(metrics, benchmark)

            total = q * self.quality_weight + v * self.value_weight + m_score * self.momentum_weight

            results.append(ScoreResult(
                symbol=symbol,
                quality_score=round(q, 4),
                value_score=round(v, 4),
                momentum_score=round(m_score, 4),
                total_score=round(total, 4),
                details={"weights": {
                    "quality": self.quality_weight,
                    "value": self.value_weight,
                    "momentum": self.momentum_weight,
                }},
            ))

        # 按总分排序
        results.sort(key=lambda x: x.total_score, reverse=True)
        return results
