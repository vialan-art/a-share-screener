"""多因子评分系统（量化增强版）。

设计思路：
1. 五维因子模型：质量(Quality) + 估值(Value) + 动量(Momentum) + 低波动(LowVol) + 稳定(Stability)
2. 每个因子内部用截面百分位排名归一化，避免量纲差异
3. 缩尾处理（Winsorization）减少极端值影响
4. Piotroski F-Score 作为质量因子子组件
5. Magic Formula（ROC + Earnings Yield）作为估值因子子组件
6. 真实价格动量：从 stock_prices 表计算 20/60/120 日收益率
7. 低波动因子：日收益率标准差越小越好
8. 行业中位数填充缺失估值字段
"""
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ScoreResult:
    symbol: str
    quality_score: float
    value_score: float
    momentum_score: float
    stability_score: float
    volatility_score: float
    total_score: float
    details: Dict[str, Any] = field(default_factory=dict)


class ScoringEngine:
    """量化评分引擎。"""

    def __init__(
        self,
        quality_weight: float = 0.25,
        value_weight: float = 0.20,
        momentum_weight: float = 0.20,
        volatility_weight: float = 0.15,
        stability_weight: float = 0.10,
        technical_weight: float = 0.10,
    ):
        total = quality_weight + value_weight + momentum_weight + volatility_weight + stability_weight + technical_weight
        self.quality_weight = quality_weight / total
        self.value_weight = value_weight / total
        self.momentum_weight = momentum_weight / total
        self.volatility_weight = volatility_weight / total
        self.stability_weight = stability_weight / total
        self.technical_weight = technical_weight / total

    @staticmethod
    def _safe_value(value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _std(values: List[float]) -> float:
        """计算样本标准差（不依赖 numpy）。"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        return math.sqrt(variance)

    @staticmethod
    def _winsorize(values: List[float], lower_pct: float = 0.02, upper_pct: float = 0.98) -> List[float]:
        clean = sorted([v for v in values if v is not None and not math.isnan(v)])
        if len(clean) < 5:
            return values
        lower = clean[int(len(clean) * lower_pct)]
        upper = clean[int(len(clean) * upper_pct)]
        return [min(max(v, lower), upper) if v is not None and not math.isnan(v) else v for v in values]

    @staticmethod
    def _percentile_rank(value: float, values: List[float], higher_is_better: bool = True) -> float:
        clean = sorted([v for v in values if v is not None and not math.isnan(v)])
        if not clean:
            return 0.5
        n = len(clean)
        below = sum(1 for v in clean if v <= value)
        pct = max(0.0, min(1.0, (below - 0.5) / n))
        return pct if higher_is_better else 1 - pct

    # ── Piotroski F-Score ─────────────────────────────────────────

    def _piotroski_score(self, metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """Piotroski F-Score (0-9)，衡量基本面强度。"""
        details = {}
        score = 0

        roa = self._safe_value(metrics.get("roa"))
        if roa is not None and roa > 0:
            score += 1; details["f_roa_positive"] = True

        ocf = self._safe_value(metrics.get("operating_cash_flow"))
        if ocf is not None and ocf > 0:
            score += 1; details["f_ocf_positive"] = True

        # ROA 增长（近似用 profit_growth 代理）
        profit_growth = self._safe_value(metrics.get("profit_growth"))
        if profit_growth is not None and profit_growth > 0:
            score += 1; details["f_profit_growing"] = True

        ocf_ratio = self._safe_value(metrics.get("ocf_to_net_profit"))
        if ocf_ratio is not None and ocf_ratio > 1.0:
            score += 1; details["f_accruals"] = True

        debt = self._safe_value(metrics.get("debt_to_asset"))
        if debt is not None and debt < 60:
            score += 1; details["f_low_leverage"] = True

        current_ratio = self._safe_value(metrics.get("current_ratio"))
        if current_ratio is not None and current_ratio > 1.0:
            score += 1; details["f_liquid"] = True

        gross_margin = self._safe_value(metrics.get("gross_margin"))
        if gross_margin is not None and gross_margin > 20:
            score += 1; details["f_margin_ok"] = True

        revenue_growth = self._safe_value(metrics.get("revenue_growth"))
        if revenue_growth is not None and revenue_growth > 0:
            score += 1; details["f_revenue_growing"] = True

        roe = self._safe_value(metrics.get("roe"))
        if roe is not None and roe > 10:
            score += 1; details["f_roe_strong"] = True

        return score / 9.0, details

    # ── Magic Formula ─────────────────────────────────────────────

    def _magic_formula_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> Tuple[float, Dict[str, Any]]:
        """Greenblatt Magic Formula：ROC + Earnings Yield 排名。"""
        details = {}

        # Earnings Yield = EBIT/EV ≈ 1/PE（越低PE越好）
        pe = self._safe_value(metrics.get("pe_ttm"))
        ey_rank = 0.5
        if pe is not None and pe > 0:
            ey = 1.0 / pe
            ey_rank = self._percentile_rank(ey, [1.0 / max(v, 0.01) for v in benchmark.get("pe_ttm", []) if v and v > 0], True)
        details["ey_rank"] = round(ey_rank, 4)

        # ROC = EBIT / (NWC + Net Fixed Assets) ≈ ROE 近似
        roe = self._safe_value(metrics.get("roe"))
        roc_rank = 0.5
        if roe is not None:
            roc_rank = self._percentile_rank(roe, benchmark.get("roe", []), True)
        details["roc_rank"] = round(roc_rank, 4)

        # 等权合并排名
        combined = (ey_rank + roc_rank) / 2
        details["magic_formula"] = round(combined, 4)
        return combined, details

    # ── Quality Factor ────────────────────────────────────────────

    def _quality_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> Tuple[float, Dict[str, Any]]:
        scores = []
        details = {}

        roe = self._safe_value(metrics.get("roe"))
        if roe is not None:
            roe_c = max(min(roe, 100.0), -50.0)
            s = self._percentile_rank(roe_c, benchmark.get("roe", []), True)
            scores.append(s); details["roe_score"] = round(s, 4)

        gross_margin = self._safe_value(metrics.get("gross_margin"))
        if gross_margin is not None:
            gm_c = max(min(gross_margin, 100.0), -50.0)
            s = self._percentile_rank(gm_c, benchmark.get("gross_margin", []), True)
            scores.append(s); details["gross_margin_score"] = round(s, 4)

        net_margin = self._safe_value(metrics.get("net_margin"))
        if net_margin is not None:
            nm_c = max(min(net_margin, 100.0), -100.0)
            s = self._percentile_rank(nm_c, benchmark.get("net_margin", []), True)
            scores.append(s); details["net_margin_score"] = round(s, 4)

        profit_growth = self._safe_value(metrics.get("profit_deducted_growth")) or self._safe_value(metrics.get("profit_growth"))
        if profit_growth is not None:
            pg_c = max(min(profit_growth, 100.0), -50.0)
            s = self._percentile_rank(pg_c, benchmark.get("profit_growth", []), True)
            scores.append(s); details["growth_score"] = round(s, 4)

        ocf_ratio = self._safe_value(metrics.get("ocf_to_net_profit"))
        if ocf_ratio is not None:
            oc_c = max(min(ocf_ratio, 10.0), -5.0)
            s = self._percentile_rank(oc_c, benchmark.get("ocf_to_net_profit", []), True)
            scores.append(s); details["ocf_ratio_score"] = round(s, 4)

        # Piotroski F-Score
        f_score, f_details = self._piotroski_score(metrics)
        scores.append(f_score)
        details["piotroski"] = round(f_score, 4)
        details["piotroski_details"] = f_details

        if not scores:
            return 0.5, details
        return sum(scores) / len(scores), details

    # ── Value Factor ──────────────────────────────────────────────

    def _value_score(self, metrics: Dict[str, Any], benchmark: Dict[str, List[float]]) -> Tuple[float, Dict[str, Any]]:
        scores = []
        details = {}

        pe = self._safe_value(metrics.get("pe_ttm"))
        if pe is not None:
            if pe > 0:
                pe_c = min(pe, 200.0)
                s = self._percentile_rank(pe_c, benchmark.get("pe_ttm", []), False)
                scores.append(s); details["pe_score"] = round(s, 4)
            else:
                scores.append(0.0); details["pe_score"] = 0.0

        pb = self._safe_value(metrics.get("pb"))
        if pb is not None:
            if pb > 0:
                pb_c = min(pb, 50.0)
                s = self._percentile_rank(pb_c, benchmark.get("pb", []), False)
                scores.append(s); details["pb_score"] = round(s, 4)
            else:
                scores.append(0.0); details["pb_score"] = 0.0

        ps = self._safe_value(metrics.get("ps_ttm"))
        if ps is not None and ps > 0:
            ps_c = min(ps, 30.0)
            s = self._percentile_rank(ps_c, benchmark.get("ps_ttm", []), False)
            scores.append(s); details["ps_score"] = round(s, 4)

        dividend_yield = self._safe_value(metrics.get("dividend_yield"))
        if dividend_yield is not None and dividend_yield >= 0:
            dy_c = min(dividend_yield, 20.0)
            s = self._percentile_rank(dy_c, benchmark.get("dividend_yield", []), True)
            scores.append(s); details["dividend_score"] = round(s, 4)

        # Magic Formula
        mf, mf_details = self._magic_formula_score(metrics, benchmark)
        scores.append(mf)
        details["magic_formula"] = mf_details

        if not scores:
            return 0.5, details
        return sum(scores) / len(scores), details

    # ── Stability Factor ──────────────────────────────────────────

    def _stability_score(self, metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        details = {}
        checks = []

        revenue_growth = self._safe_value(metrics.get("revenue_growth"))
        profit_growth = self._safe_value(metrics.get("profit_growth"))
        profit_deducted = self._safe_value(metrics.get("profit_deducted_growth"))
        ocf_ratio = self._safe_value(metrics.get("ocf_to_net_profit"))

        if revenue_growth is not None:
            ok = revenue_growth >= 0
            checks.append(ok); details["revenue_growing"] = ok

        if profit_growth is not None:
            ok = profit_growth >= 0
            checks.append(ok); details["profit_growing"] = ok

        if profit_deducted is not None:
            ok = profit_deducted >= 0
            checks.append(ok); details["profit_deducted_growing"] = ok

        if ocf_ratio is not None:
            ok = ocf_ratio >= 0.8
            checks.append(ok); details["ocf_strong"] = ok

        if not checks:
            return 0.5, details
        return sum(checks) / len(checks), details

    # ── Momentum Factor (from price history) ──────────────────────

    def _momentum_score(
        self,
        metrics: Dict[str, Any],
        benchmark: Dict[str, List[float]],
        price_momentum: Optional[Dict[str, float]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        scores = []
        details = {}

        # 真实价格动量
        if price_momentum:
            for period, ret in price_momentum.items():
                key = f"mom_{period}"
                if ret is not None and key in benchmark:
                    s = self._percentile_rank(ret, benchmark[key], True)
                    scores.append(s)
                    details[f"momentum_{period}"] = round(s, 4)
                    details[f"return_{period}"] = round(ret * 100, 2)

        # 换手率作为流动性参考（低权重）
        turnover = self._safe_value(metrics.get("turnover"))
        if turnover is not None:
            if turnover > 15.0 or turnover < 0.1:
                s = 0.3
            else:
                s = self._percentile_rank(turnover, benchmark.get("turnover", []), True)
            scores.append(s * 0.3)  # 换手率只占 30% 权重
            details["turnover_score"] = round(s, 4)

        if not scores:
            return 0.5, details
        return sum(scores) / len(scores), details

    # ── Volatility Factor (low vol anomaly) ───────────────────────

    def _volatility_score(
        self,
        benchmark: Dict[str, List[float]],
        daily_returns: Optional[List[float]] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        details = {}

        if daily_returns and len(daily_returns) >= 10:
            vol = self._std(daily_returns)
            details["daily_vol"] = round(vol * 100, 3)

            if "daily_vol" in benchmark and benchmark["daily_vol"]:
                # 低波动 → 高分（低波动异象）
                s = self._percentile_rank(vol, benchmark["daily_vol"], False)
                details["vol_score"] = round(s, 4)
                return s, details

        return 0.5, details

    # ── Technical Factor ──────────────────────────────────────────

    def _technical_score(self, metrics: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
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

        weights = {"indicator": 0.35, "pattern": 0.20, "strategy": 0.20, "fundamental": 0.15, "sentiment": 0.10}
        tw = sum(w for t, w in weights.items() if t in by_type)
        if tw == 0:
            return 0.5, {"note": "无可用插件分数"}

        score = sum(_avg(by_type.get(t, [])) * w for t, w in weights.items() if t in by_type) / tw
        details = {t: round(_avg(scores), 4) for t, scores in by_type.items()}
        return round(score, 4), details

    # ── Benchmark Builder ─────────────────────────────────────────

    def _build_benchmark(self, all_metrics: List[Dict[str, Any]]) -> Dict[str, List[float]]:
        benchmark = {
            "roe": [], "gross_margin": [], "net_margin": [],
            "profit_growth": [], "profit_deducted_growth": [],
            "ocf_to_net_profit": [],
            "pe_ttm": [], "pb": [], "ps_ttm": [], "dividend_yield": [],
            "turnover": [],
        }
        for m in all_metrics:
            for key in benchmark:
                v = self._safe_value(m.get(key))
                if v is not None:
                    benchmark[key].append(v)
        for key in benchmark:
            benchmark[key] = self._winsorize(benchmark[key])
        return benchmark

    def add_price_benchmarks(
        self,
        benchmark: Dict[str, List[float]],
        momentum_map: Dict[str, Dict[str, float]],
        volatility_map: Dict[str, List[float]],
    ):
        """把价格动量和波动率加入 benchmark 用于截面排名。"""
        for period in ["20d", "60d", "120d"]:
            key = f"mom_{period}"
            benchmark[key] = []
            for sym, mom in momentum_map.items():
                v = mom.get(period)
                if v is not None:
                    benchmark[key].append(v)
            benchmark[key] = self._winsorize(benchmark[key])

        benchmark["daily_vol"] = []
        for sym, rets in volatility_map.items():
            if len(rets) >= 10:
                benchmark["daily_vol"].append(self._std(rets))
        benchmark["daily_vol"] = self._winsorize(benchmark["daily_vol"])

    # ── Main Entry ────────────────────────────────────────────────

    def _impute_missing_values(
        self,
        stocks: List[Dict[str, Any]],
        metrics_map: Dict[str, Dict[str, Any]],
    ):
        """用行业中位数填充缺失的 PE/PB/PS 等估值字段。"""
        industry_groups: Dict[str, List[Dict[str, Any]]] = {}
        for s in stocks:
            m = metrics_map.get(s["symbol"], {})
            ind = m.get("industry") or s.get("industry") or "unknown"
            industry_groups.setdefault(ind, []).append(m)

        impute_fields = ["pe_ttm", "pb", "ps_ttm", "turnover"]
        for ind, group in industry_groups.items():
            for field in impute_fields:
                values = [self._safe_value(m.get(field)) for m in group]
                clean = [v for v in values if v is not None and v > 0]
                if not clean:
                    continue
                median = sorted(clean)[len(clean) // 2]
                for m in group:
                    if self._safe_value(m.get(field)) is None:
                        m[field] = round(median, 2)
                        note = m.get("data_source_note", "")
                        m["data_source_note"] = f"{note}; {field} 用行业({ind})中位数填充" if note else f"{field} 用行业({ind})中位数填充"

    def score_batch(
        self,
        stocks: List[Dict[str, Any]],
        metrics_map: Dict[str, Dict[str, Any]],
        momentum_map: Optional[Dict[str, Dict[str, float]]] = None,
        volatility_map: Optional[Dict[str, List[float]]] = None,
    ) -> List[ScoreResult]:
        # 先用行业中位数填充缺失估值
        self._impute_missing_values(stocks, metrics_map)

        all_metrics = list(metrics_map.values())
        benchmark = self._build_benchmark(all_metrics)

        if momentum_map and volatility_map:
            self.add_price_benchmarks(benchmark, momentum_map, volatility_map)

        results = []
        for stock in stocks:
            symbol = stock["symbol"]
            metrics = metrics_map.get(symbol, {})

            q, q_det = self._quality_score(metrics, benchmark)
            v, v_det = self._value_score(metrics, benchmark)
            s, s_det = self._stability_score(metrics)
            m_sc, m_det = self._momentum_score(
                metrics, benchmark,
                price_momentum=(momentum_map or {}).get(symbol),
            )
            vol_sc, vol_det = self._volatility_score(
                benchmark,
                daily_returns=(volatility_map or {}).get(symbol),
            )
            t_sc, t_det = self._technical_score(metrics)

            total = (
                q * self.quality_weight
                + v * self.value_weight
                + s * self.stability_weight
                + m_sc * self.momentum_weight
                + vol_sc * self.volatility_weight
                + t_sc * self.technical_weight
            )

            results.append(ScoreResult(
                symbol=symbol,
                quality_score=round(q, 4),
                value_score=round(v, 4),
                momentum_score=round(m_sc, 4),
                stability_score=round(s, 4),
                volatility_score=round(vol_sc, 4),
                total_score=round(total, 4),
                details={
                    "weights": {
                        "quality": self.quality_weight,
                        "value": self.value_weight,
                        "stability": self.stability_weight,
                        "momentum": self.momentum_weight,
                        "volatility": self.volatility_weight,
                        "technical": self.technical_weight,
                    },
                    "quality": q_det, "value": v_det, "stability": s_det,
                    "momentum": m_det, "volatility": vol_det, "technical": t_det,
                },
            ))

        results.sort(key=lambda x: x.total_score, reverse=True)
        return results
