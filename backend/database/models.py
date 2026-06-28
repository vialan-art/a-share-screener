"""数据库表模型定义。"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from backend.database.connection import Base


class Stock(Base):
    """股票基础信息表。"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), unique=True, index=True, comment="股票代码，如 000001")
    name = Column(String(100), comment="股票名称")
    industry = Column(String(100), comment="所属行业")
    sector = Column(String(100), comment="所属板块")
    market = Column(String(20), comment="交易所，如 SZ/SH")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinancialMetric(Base):
    """财务指标表（最新一期）。"""
    __tablename__ = "financial_metrics"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    report_period = Column(String(20), comment="报告期，如 2024-03-31")

    # 盈利能力
    roe = Column(Float, comment="净资产收益率 ROE (%)")
    roa = Column(Float, comment="总资产收益率 ROA (%)")
    gross_margin = Column(Float, comment="毛利率 (%)")
    net_margin = Column(Float, comment="净利率 (%)")

    # 成长能力
    revenue_growth = Column(Float, comment="营收同比增长率 (%)")
    profit_growth = Column(Float, comment="净利润同比增长率 (%)")

    # 偿债与运营
    debt_to_asset = Column(Float, comment="资产负债率 (%)")
    current_ratio = Column(Float, comment="流动比率")

    # 现金流
    operating_cash_flow = Column(Float, comment="经营活动现金流净额（亿元）")
    operating_cash_flow_growth = Column(Float, comment="经营现金流同比增长率 (%)")

    # 估值
    pe_ttm = Column(Float, comment="市盈率 TTM")
    pb = Column(Float, comment="市净率")
    ps_ttm = Column(Float, comment="市销率 TTM")
    dividend_yield = Column(Float, comment="股息率 (%)")

    # 审计意见（关键红线）
    audit_opinion = Column(String(100), comment="审计意见")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class StockScore(Base):
    """评分结果表。"""
    __tablename__ = "stock_scores"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True)
    score_date = Column(DateTime, default=datetime.utcnow, comment="评分日期")

    quality_score = Column(Float, comment="质量分")
    value_score = Column(Float, comment="估值分")
    momentum_score = Column(Float, comment="动量分")
    total_score = Column(Float, comment="综合得分")

    passed_filters = Column(Boolean, comment="是否通过及格线")
    filter_reasons = Column(Text, comment="未通过原因，JSON 列表")


class DailySnapshot(Base):
    """每日选股结果快照。"""
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(String(20), index=True, comment="快照日期，如 2024-06-28")
    symbol = Column(String(20), index=True)
    name = Column(String(100))
    industry = Column(String(100))
    total_score = Column(Float)
    quality_score = Column(Float)
    value_score = Column(Float)
    momentum_score = Column(Float)
    pe_ttm = Column(Float)
    pb = Column(Float)
    roe = Column(Float)
    debt_to_asset = Column(Float)
    data_json = Column(Text, comment="该日完整数据 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)


class UpdateLog(Base):
    """数据更新日志。"""
    __tablename__ = "update_logs"

    id = Column(Integer, primary_key=True, index=True)
    update_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), comment="success / partial / failed")
    message = Column(Text)
    stocks_count = Column(Integer)
