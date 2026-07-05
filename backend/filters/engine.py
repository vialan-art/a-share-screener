"""及格线过滤系统（生产级优化）。

设计理念：
1. 先排除有硬伤的公司（审计非标、亏损、高负债、现金流差、估值过高）
2. 不同行业可以有不同的及格线
3. 过滤结果会记录原因，方便调试和学习
4. 对缺失数据采取保守策略：关键字段缺失时默认不通过
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

    # 通用默认及格线（严格版）
    # 目标：只保留基本面健康、估值合理、有盈利增长的公司
    DEFAULT_RULES = {
        "audit_opinion_required": "标准无保留意见",
        "min_roe": 8.0,
        "max_debt_to_asset": 75.0,
        "max_interest_bearing_debt_ratio": 60.0,
        "min_profit_growth": -5.0,
        "min_revenue_growth": -10.0,
        "min_operating_cash_flow": 0.0,
        "min_ocf_to_net_profit": 0.3,
        "max_pe_ttm": 55.0,
        "max_ps_ttm": 30.0,
        "min_pb": 0.0,
        "max_pb": 12.0,
    }

    # 行业特例
    INDUSTRY_RULES = {
        "银行": {
            "min_roe": 8.0,
            "max_debt_to_asset": 95.0,
            "max_interest_bearing_debt_ratio": 95.0,
            "max_pe_ttm": 15.0,
        },
        "保险": {
            "min_roe": 8.0,
            "max_debt_to_asset": 95.0,
            "max_interest_bearing_debt_ratio": 95.0,
        },
        "房地产": {
            "min_roe": 5.0,
            "max_debt_to_asset": 85.0,
            "min_profit_growth": -20.0,  # 行业周期下行，容忍度稍高
        },
        "电力": {
            "min_roe": 4.0,
            "max_debt_to_asset": 75.0,
        },
        "煤炭": {
            "min_roe": 10.0,
            "max_debt_to_asset": 65.0,
            "min_profit_growth": -20.0,  # 周期性行业
        },
        "食品饮料": {
            "min_roe": 12.0,
            "max_debt_to_asset": 55.0,
            "max_pe_ttm": 40.0,
        },
        "医药生物": {
            "min_roe": 8.0,
            "max_debt_to_asset": 55.0,
        },
        "白酒Ⅱ": {
            "min_roe": 12.0,
            "max_debt_to_asset": 55.0,
            "max_pe_ttm": 40.0,
        },
        "白酒": {
            "min_roe": 12.0,
            "max_debt_to_asset": 55.0,
            "max_pe_ttm": 40.0,
        },
    }

    def __init__(self, custom_rules: Dict[str, Any] = None, strict_mode: bool = True):
        self.custom_rules = custom_rules or {}
        self.strict_mode = strict_mode

    def _get_rules(self, industry: str) -> Dict[str, Any]:
        """合并默认规则、行业规则、自定义规则。"""
        rules = dict(self.DEFAULT_RULES)
        if industry in self.INDUSTRY_RULES:
            rules.update(self.INDUSTRY_RULES[industry])
        rules.update(self.custom_rules)
        return rules

    @staticmethod
    def _safe_float(value) -> float:
        """安全转 float，无效值返回 None。"""
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

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
                if audit:
                    reasons.append(f"审计意见不合规: {audit}")
                elif self.strict_mode:
                    reasons.append("缺少审计意见")

        # 2. ROE 检查
        roe = self._safe_float(metrics.get("roe"))
        min_roe = rules.get("min_roe")
        if roe is not None and min_roe is not None and roe < min_roe:
            reasons.append(f"ROE 过低: {roe:.2f}% < {min_roe}%")

        # 3. 资产负债率检查
        debt = self._safe_float(metrics.get("debt_to_asset"))
        max_debt = rules.get("max_debt_to_asset")
        if debt is not None and max_debt is not None and debt > max_debt:
            reasons.append(f"负债率过高: {debt:.2f}% > {max_debt}%")

        # 4. 有息负债率检查
        ibd = self._safe_float(metrics.get("interest_bearing_debt_ratio"))
        max_ibd = rules.get("max_interest_bearing_debt_ratio")
        if ibd is not None and max_ibd is not None and ibd > max_ibd:
            reasons.append(f"有息负债率过高: {ibd:.2f}% > {max_ibd}%")

        # 5. 营收增长检查
        revenue_growth = self._safe_float(metrics.get("revenue_growth"))
        min_revenue_growth = rules.get("min_revenue_growth")
        if revenue_growth is not None and min_revenue_growth is not None and revenue_growth < min_revenue_growth:
            reasons.append(f"营收增长过低: {revenue_growth:.2f}% < {min_revenue_growth}%")

        # 6. 净利润增长检查
        profit_growth = self._safe_float(metrics.get("profit_growth"))
        min_profit_growth = rules.get("min_profit_growth")
        if profit_growth is not None and min_profit_growth is not None and profit_growth < min_profit_growth:
            reasons.append(f"净利润增长过低: {profit_growth:.2f}% < {min_profit_growth}%")

        # 7. 经营现金流检查
        ocf = self._safe_float(metrics.get("operating_cash_flow"))
        min_ocf = rules.get("min_operating_cash_flow")
        if ocf is not None and min_ocf is not None and ocf < min_ocf:
            reasons.append(f"经营现金流为负: {ocf:.2f}亿 < {min_ocf}亿")

        # 8. 经营现金流/净利润检查
        ocf_ratio = self._safe_float(metrics.get("ocf_to_net_profit"))
        min_ocf_ratio = rules.get("min_ocf_to_net_profit")
        if ocf_ratio is not None and min_ocf_ratio is not None and ocf_ratio < min_ocf_ratio:
            reasons.append(f"经营现金流覆盖不足: {ocf_ratio:.2f} < {min_ocf_ratio}")

        # 9. PE / PS 检查：亏损股不直接淘汰，结合市销率和增长趋势
        pe = self._safe_float(metrics.get("pe_ttm"))
        ps = self._safe_float(metrics.get("ps_ttm"))
        max_pe = rules.get("max_pe_ttm")
        max_ps = rules.get("max_ps_ttm", 30.0)

        if pe is not None and max_pe is not None:
            if pe <= 0:
                # 亏损股：用 PS 和增长趋势判断是否有转盈预期
                loss_reasons = []
                if ps is None or ps <= 0 or ps > max_ps:
                    loss_reasons.append(
                        f"亏损且市销率不合理: PS={ps:.2f}" if ps is not None else "亏损且缺少市销率"
                    )
                if revenue_growth is None or revenue_growth < 0:
                    loss_reasons.append("亏损且营收下滑")
                if profit_growth is None or profit_growth < 0:
                    loss_reasons.append("亏损且利润未改善")
                if loss_reasons:
                    reasons.extend(loss_reasons)
            elif pe > max_pe:
                reasons.append(f"PE 过高: {pe:.2f} > {max_pe}")

        # 10. PB 检查
        pb = self._safe_float(metrics.get("pb"))
        min_pb = rules.get("min_pb")
        max_pb = rules.get("max_pb")
        if pb is not None:
            if min_pb is not None and pb <= min_pb:
                reasons.append(f"PB 异常: PB={pb:.2f}")
            elif max_pb is not None and pb > max_pb:
                reasons.append(f"PB 过高: {pb:.2f} > {max_pb}")

        passed = len(reasons) == 0
        return FilterResult(symbol=symbol, passed=passed, reasons=reasons)

    def evaluate_batch(self, stocks: List[Dict[str, Any]], metrics_map: Dict[str, Dict[str, Any]]) -> List[FilterResult]:
        """批量过滤。"""
        results = []
        for stock in stocks:
            metrics = metrics_map.get(stock["symbol"], {})
            results.append(self.evaluate(stock, metrics))
        return results
