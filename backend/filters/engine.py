"""及格线过滤系统。

设计理念：
1. 先排除有硬伤的公司（审计非标、亏损、高负债、现金流差）
2. 不同行业可以有不同的及格线
3. 过滤结果会记录原因，方便调试和学习
"""
from typing import List, Dict, Any
from dataclasses import dataclass


@dataclass
class FilterResult:
    """单只股票的过滤结果。"""
    symbol: str
    passed: bool
    reasons: List[str]


class FilterEngine:
    """过滤引擎。"""

    # 通用默认及格线
    DEFAULT_RULES = {
        "audit_opinion_required": "标准无保留意见",
        "min_roe": 5.0,
        "max_debt_to_asset": 85.0,
        "max_interest_bearing_debt_ratio": 75.0,
        "min_profit_growth": -50.0,
        "min_operating_cash_flow": -10.0,
    }

    # 行业特例
    INDUSTRY_RULES = {
        "银行": {
            "min_roe": 8.0,
            "max_debt_to_asset": 95.0,
            "max_interest_bearing_debt_ratio": 95.0,
        },
        "保险": {
            "min_roe": 8.0,
            "max_debt_to_asset": 95.0,
            "max_interest_bearing_debt_ratio": 95.0,
        },
        "房地产": {
            "min_roe": 5.0,
            "max_debt_to_asset": 90.0,
        },
        "电力": {
            "min_roe": 4.0,
            "max_debt_to_asset": 80.0,
        },
        "煤炭": {
            "min_roe": 8.0,
            "max_debt_to_asset": 70.0,
        },
        "食品饮料": {
            "min_roe": 10.0,
            "max_debt_to_asset": 60.0,
        },
        "医药生物": {
            "min_roe": 8.0,
            "max_debt_to_asset": 60.0,
        },
    }

    def __init__(self, custom_rules: Dict[str, Any] = None):
        self.custom_rules = custom_rules or {}

    def _get_rules(self, industry: str) -> Dict[str, Any]:
        """合并默认规则、行业规则、自定义规则。"""
        rules = dict(self.DEFAULT_RULES)
        if industry in self.INDUSTRY_RULES:
            rules.update(self.INDUSTRY_RULES[industry])
        rules.update(self.custom_rules)
        return rules

    def evaluate(self, stock: Dict[str, Any], metrics: Dict[str, Any]) -> FilterResult:
        """对一只股票进行及格线检查。"""
        symbol = stock.get("symbol", "")
        industry = stock.get("industry", "未知")
        rules = self._get_rules(industry)

        reasons = []

        # 1. 审计意见红线
        audit = metrics.get("audit_opinion", "") or ""
        if rules.get("audit_opinion_required"):
            required = rules["audit_opinion_required"]
            if required not in audit and "无保留" not in audit:
                reasons.append(f"审计意见不合规: {audit or '未知'}")

        # 2. ROE 检查
        roe = metrics.get("roe")
        min_roe = rules.get("min_roe")
        if roe is not None and min_roe is not None and roe < min_roe:
            reasons.append(f"ROE 过低: {roe:.2f}% < {min_roe}%")

        # 3. 资产负债率检查
        debt = metrics.get("debt_to_asset")
        max_debt = rules.get("max_debt_to_asset")
        if debt is not None and max_debt is not None and debt > max_debt:
            reasons.append(f"负债率过高: {debt:.2f}% > {max_debt}%")

        # 4. 有息负债率检查
        ibd = metrics.get("interest_bearing_debt_ratio")
        max_ibd = rules.get("max_interest_bearing_debt_ratio")
        if ibd is not None and max_ibd is not None and ibd > max_ibd:
            reasons.append(f"有息负债率过高: {ibd:.2f}% > {max_ibd}%")

        # 5. 净利润增长检查
        profit_growth = metrics.get("profit_growth")
        min_profit_growth = rules.get("min_profit_growth")
        if profit_growth is not None and min_profit_growth is not None and profit_growth < min_profit_growth:
            reasons.append(f"净利润增长过低: {profit_growth:.2f}% < {min_profit_growth}%")

        # 6. 经营现金流检查
        ocf = metrics.get("operating_cash_flow")
        min_ocf = rules.get("min_operating_cash_flow")
        if ocf is not None and min_ocf is not None and ocf < min_ocf:
            reasons.append(f"经营现金流过低: {ocf:.2f}亿 < {min_ocf}亿")

        passed = len(reasons) == 0
        return FilterResult(symbol=symbol, passed=passed, reasons=reasons)

    def evaluate_batch(self, stocks: List[Dict[str, Any]], metrics_map: Dict[str, Dict[str, Any]]) -> List[FilterResult]:
        """批量过滤。"""
        results = []
        for stock in stocks:
            metrics = metrics_map.get(stock["symbol"], {})
            results.append(self.evaluate(stock, metrics))
        return results
