"""stock-scanner 集成插件。

提取 stock-scanner 中两个可落地的规则模块：
1. 25 项财务指标健康度打分（完全基于现有 metrics，无需额外网络请求）。
2. 基于中文情感词库的新闻情绪打分（对过滤后股票按需拉取新闻）。

不引入其 Web/AI/Agent 层，保持轻量。
"""
from typing import Any, Dict, List, Optional

from backend.plugins.base import BaseSignalPlugin, SignalResult
from backend.plugins.registry import register_plugin


@register_plugin
class StockScannerFundamentalPlugin(BaseSignalPlugin):
    """stock-scanner 财务健康度打分。

    参考其 calculate_fundamental_score，把 0-100 原始分映射到 0-1。
    """

    name = "stock_scanner_fundamental"
    signal_type = "fundamental"

    # 与基本面相关的常见字段，用于判断指标丰富度
    FUNDAMENTAL_FIELDS = [
        "roe", "roa", "gross_margin", "net_margin",
        "revenue_growth", "profit_growth", "profit_deducted_growth",
        "debt_to_asset", "current_ratio", "quick_ratio",
        "total_assets", "total_equity", "operating_cash_flow",
        "ocf_to_net_profit", "pe_ttm", "pb", "ps_ttm",
        "market_cap", "turnover", "dividend_yield",
    ]

    def compute(
        self,
        symbol: str,
        metrics: Dict[str, Any],
        ohlcv: Optional[List[Dict[str, Any]]] = None,
    ) -> SignalResult:
        score = 50
        reasons: List[str] = []

        valid_count = sum(
            1 for f in self.FUNDAMENTAL_FIELDS if self._safe_float(metrics.get(f)) is not None
        )
        if valid_count >= 15:
            score += 20
            reasons.append(f"{valid_count}项指标可用")

        roe = self._safe_float(metrics.get("roe"))
        if roe is not None:
            if roe > 15:
                score += 10
                reasons.append("ROE>15%")
            elif roe > 10:
                score += 5
                reasons.append("ROE>10%")
            elif roe < 5:
                score -= 5
                reasons.append("ROE<5%")

        debt = self._safe_float(metrics.get("debt_to_asset"))
        if debt is not None:
            if debt < 30:
                score += 5
                reasons.append("资产负债率<30%")
            elif debt > 70:
                score -= 10
                reasons.append("资产负债率>70%")

        rev_growth = self._safe_float(metrics.get("revenue_growth"))
        if rev_growth is not None:
            if rev_growth > 20:
                score += 10
                reasons.append("营收增长>20%")
            elif rev_growth > 10:
                score += 5
                reasons.append("营收增长>10%")
            elif rev_growth < -10:
                score -= 10
                reasons.append("营收下滑>10%")

        has_valuation = any(
            self._safe_float(metrics.get(k)) is not None for k in ["pe_ttm", "pb", "ps_ttm"]
        )
        if has_valuation:
            score += 10
            reasons.append("估值指标可用")

        score = max(0, min(100, score))

        return SignalResult(
            symbol=symbol,
            name=self.name,
            signal_type=self.signal_type,
            value={"raw_score": score, "valid_indicators": valid_count},
            score=round(score / 100.0, 4),
            passed=score >= 60,
            reason="; ".join(reasons) if reasons else "财务指标一般",
        )


@register_plugin
class StockScannerSentimentPlugin(BaseSignalPlugin):
    """stock-scanner 新闻情绪打分。

    对过滤后股票按需拉取东方财富新闻、公告、研报，
    使用其中文情感词库做轻量规则打分，映射到 0-1。
    """

    name = "stock_scanner_sentiment"
    signal_type = "sentiment"

    POSITIVE_WORDS = {
        "上涨", "涨停", "利好", "突破", "增长", "盈利", "收益", "回升", "强势", "看好",
        "买入", "推荐", "优秀", "领先", "创新", "发展", "机会", "潜力", "稳定", "改善",
        "提升", "超预期", "积极", "乐观", "向好", "受益", "龙头", "热点", "爆发", "翻倍",
        "业绩", "增收", "扩张", "合作", "签约", "中标", "获得", "成功", "完成", "达成",
    }
    NEGATIVE_WORDS = {
        "下跌", "跌停", "利空", "破位", "下滑", "亏损", "风险", "回调", "弱势", "看空",
        "卖出", "减持", "较差", "落后", "滞后", "困难", "危机", "担忧", "悲观", "恶化",
        "下降", "低于预期", "消极", "压力", "套牢", "被套", "暴跌", "崩盘", "踩雷", "退市",
        "违规", "处罚", "调查", "停牌", "债务", "违约", "诉讼", "纠纷", "问题",
    }

    # 测试中可通过 metrics["_news_data"] 注入新闻，避免网络请求
    def _collect_texts(self, symbol: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        injected = metrics.get("_news_data")
        if injected is not None:
            return injected

        try:
            import akshare as ak
        except Exception:
            return []

        texts: List[Dict[str, Any]] = []

        try:
            df = ak.stock_news_em(symbol=symbol)
            for _, row in df.head(20).iterrows():
                text = " ".join(str(v) for v in row.values if v is not None)
                texts.append({"text": text, "type": "company_news", "weight": 1.0})
        except Exception:
            pass

        try:
            df = ak.stock_zh_a_alerts_cls(symbol=symbol)
            for _, row in df.head(20).iterrows():
                text = " ".join(str(v) for v in row.values if v is not None)
                texts.append({"text": text, "type": "announcement", "weight": 1.2})
        except Exception:
            pass

        try:
            df = ak.stock_research_report_em(symbol=symbol)
            for _, row in df.head(20).iterrows():
                parts = [str(v) for v in row.values if v is not None]
                text = " ".join(parts)
                texts.append({"text": text, "type": "research_report", "weight": 0.9})
        except Exception:
            pass

        return texts

    def _analyze_texts(self, texts: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not texts:
            return {
                "overall_sentiment": 0.0,
                "confidence_score": 0.0,
                "total_analyzed": 0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
            }

        scores: List[float] = []
        for item in texts:
            text = str(item.get("text", ""))
            weight = float(item.get("weight", 1.0))
            if not text.strip():
                continue

            positive = sum(1 for word in self.POSITIVE_WORDS if word in text)
            negative = sum(1 for word in self.NEGATIVE_WORDS if word in text)
            total = positive + negative
            if total > 0:
                sentiment = (positive - negative) / total
            else:
                sentiment = 0.0
            scores.append(sentiment * weight)

        if not scores:
            return {
                "overall_sentiment": 0.0,
                "confidence_score": 0.0,
                "total_analyzed": len(texts),
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
            }

        overall = sum(scores) / len(scores)
        confidence = min(len(texts) / 50, 1.0)
        positive_ratio = len([s for s in scores if s > 0]) / len(scores)
        negative_ratio = len([s for s in scores if s < 0]) / len(scores)

        return {
            "overall_sentiment": round(overall, 4),
            "confidence_score": round(confidence, 4),
            "total_analyzed": len(texts),
            "positive_ratio": round(positive_ratio, 4),
            "negative_ratio": round(negative_ratio, 4),
        }

    def compute(
        self,
        symbol: str,
        metrics: Dict[str, Any],
        ohlcv: Optional[List[Dict[str, Any]]] = None,
    ) -> SignalResult:
        texts = self._collect_texts(symbol, metrics)
        if not texts:
            return SignalResult(
                symbol=symbol,
                name=self.name,
                signal_type=self.signal_type,
                value={"overall_sentiment": 0.0, "total_analyzed": 0},
                score=0.5,
                passed=False,
                reason="无新闻数据",
            )

        analysis = self._analyze_texts(texts)
        overall = analysis["overall_sentiment"]
        confidence = analysis["confidence_score"]
        total = analysis["total_analyzed"]

        base_score = (overall + 1) * 50
        final_score = base_score + confidence * 10 + min(total / 100, 1.0) * 10
        final_score = max(0, min(100, final_score))

        if overall > 0.3:
            trend = "非常积极"
        elif overall > 0.1:
            trend = "偏向积极"
        elif overall > -0.1:
            trend = "相对中性"
        elif overall > -0.3:
            trend = "偏向消极"
        else:
            trend = "非常消极"

        return SignalResult(
            symbol=symbol,
            name=self.name,
            signal_type=self.signal_type,
            value=analysis,
            score=round(final_score / 100.0, 4),
            passed=overall > 0.1,
            reason=trend,
        )
