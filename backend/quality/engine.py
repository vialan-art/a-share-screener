"""数据质量校验与追踪模块。

目标：
1. 计算每条记录的字段完整度
2. 识别异常值和可疑数据
3. 记录数据来源和更新时间
4. 给用户提供透明的数据可信度信息

重要原则：
- 不隐藏数据问题
- 所有指标都标注来源和不确定性
- 不对无法验证的数据做过度承诺
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
import math


# 关键字段及其期望的数据类型/范围
CRITICAL_FIELDS = {
    "roe": {"label": "ROE", "min": -100, "max": 100, "unit": "%"},
    "roa": {"label": "ROA", "min": -100, "max": 100, "unit": "%"},
    "gross_margin": {"label": "毛利率", "min": -100, "max": 100, "unit": "%"},
    "net_margin": {"label": "净利率", "min": -100, "max": 100, "unit": "%"},
    "revenue_growth": {"label": "营收增长", "min": -100, "max": 500, "unit": "%"},
    "profit_growth": {"label": "净利润增长", "min": -100, "max": 500, "unit": "%"},
    "profit_deducted_growth": {"label": "扣非净利润增长", "min": -100, "max": 500, "unit": "%"},
    "debt_to_asset": {"label": "资产负债率", "min": 0, "max": 100, "unit": "%"},
    "interest_bearing_debt_ratio": {"label": "有息负债率", "min": 0, "max": 100, "unit": "%"},
    "current_ratio": {"label": "流动比率", "min": 0, "max": 50},
    "quick_ratio": {"label": "速动比率", "min": 0, "max": 50},
    "operating_cash_flow": {"label": "经营现金流", "min": -10000, "max": 10000, "unit": "亿"},
    "free_cash_flow": {"label": "自由现金流", "min": -10000, "max": 10000, "unit": "亿"},
    "ocf_to_net_profit": {"label": "经营现金流/净利润", "min": -50, "max": 50},
    "pe_ttm": {"label": "PE TTM", "min": -10000, "max": 10000},
    "pb": {"label": "PB", "min": -100, "max": 100},
    "dividend_yield": {"label": "股息率", "min": 0, "max": 50, "unit": "%"},
}


class DataQualityReport:
    """单只股票的数据质量报告。"""

    def __init__(self, symbol: str, metrics: Dict[str, Any], source: str, freshness: datetime):
        self.symbol = symbol
        self.metrics = metrics
        self.source = source
        self.freshness = freshness
        self.issues: List[str] = []
        self.completeness_score = 0.0
        self._evaluate()

    def _evaluate(self):
        """评估数据完整性和异常值。"""
        total_fields = len(CRITICAL_FIELDS)
        present_fields = 0

        for field, meta in CRITICAL_FIELDS.items():
            value = self.metrics.get(field)

            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue

            present_fields += 1

            # 范围检查
            if isinstance(value, (int, float)):
                min_v = meta.get("min")
                max_v = meta.get("max")
                if min_v is not None and value < min_v:
                    self.issues.append(f"{meta['label']} 异常偏低: {value}")
                if max_v is not None and value > max_v:
                    self.issues.append(f"{meta['label']} 异常偏高: {value}")

        self.completeness_score = round(present_fields / total_fields, 4) if total_fields > 0 else 0.0

        # 特别检查：审计意见
        audit = self.metrics.get("audit_opinion", "")
        if not audit:
            self.issues.append("缺少审计意见")

        # 特别检查：PE 为负（亏损公司）
        pe = self.metrics.get("pe_ttm")
        if isinstance(pe, (int, float)) and pe < 0:
            self.issues.append("PE TTM 为负，公司可能亏损")

        # 特别检查：现金流长期为负
        fcf = self.metrics.get("free_cash_flow")
        ocf = self.metrics.get("operating_cash_flow")
        if isinstance(fcf, (int, float)) and isinstance(ocf, (int, float)) and fcf < 0 and ocf < 0:
            self.issues.append("经营现金流和自由现金流同时为负")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "source": self.source,
            "freshness": self.freshness.isoformat() if self.freshness else None,
            "completeness_score": self.completeness_score,
            "issues": self.issues,
            "is_reliable": len(self.issues) == 0 and self.completeness_score >= 0.7,
        }


class DataQualityEngine:
    """批量数据质量评估。"""

    @staticmethod
    def evaluate_all(metrics_map: Dict[str, Dict[str, Any]], source: str, freshness: datetime) -> Dict[str, DataQualityReport]:
        reports = {}
        for symbol, metrics in metrics_map.items():
            reports[symbol] = DataQualityReport(symbol, metrics, source, freshness)
        return reports

    @staticmethod
    def average_completeness(reports: Dict[str, DataQualityReport]) -> float:
        if not reports:
            return 0.0
        return round(sum(r.completeness_score for r in reports.values()) / len(reports), 4)

    @staticmethod
    def enrich_metrics_with_quality(
        metrics_map: Dict[str, Dict[str, Any]],
        reports: Dict[str, DataQualityReport],
    ) -> Dict[str, Dict[str, Any]]:
        """把质量报告合并到 metrics 中，方便后续持久化。"""
        enriched = {}
        for symbol, metrics in metrics_map.items():
            report = reports.get(symbol)
            m = dict(metrics)
            if report:
                m["data_source"] = report.source
                m["data_freshness"] = report.freshness
                m["completeness_score"] = report.completeness_score
            enriched[symbol] = m
        return enriched
