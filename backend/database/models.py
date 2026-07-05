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
    revenue = Column(Float, comment="营业收入（亿元）")
    revenue_growth = Column(Float, comment="营收同比增长率 (%)")
    net_profit = Column(Float, comment="净利润（亿元）")
    profit_growth = Column(Float, comment="净利润同比增长率 (%)")
    net_profit_deducted = Column(Float, comment="扣非净利润（亿元）")
    profit_deducted_growth = Column(Float, comment="扣非净利润同比增长率 (%)")

    # 偿债与运营
    debt_to_asset = Column(Float, comment="资产负债率 (%)")
    interest_bearing_debt_ratio = Column(Float, comment="有息负债率 (%)")
    current_ratio = Column(Float, comment="流动比率")
    quick_ratio = Column(Float, comment="速动比率")
    total_assets = Column(Float, comment="总资产（亿元）")
    total_equity = Column(Float, comment="净资产（亿元）")

    # 现金流
    operating_cash_flow = Column(Float, comment="经营活动现金流净额（亿元）")
    operating_cash_flow_growth = Column(Float, comment="经营现金流同比增长率 (%)")
    capital_expenditure = Column(Float, comment="资本支出（亿元），取负值")
    free_cash_flow = Column(Float, comment="自由现金流（亿元）")
    ocf_to_net_profit = Column(Float, comment="经营现金流/净利润")

    # 估值（行情数据每日更新）
    latest_price = Column(Float, comment="最新价")
    change_pct = Column(Float, comment="涨跌幅 (%)")
    turnover = Column(Float, comment="换手率 (%)")
    pe_ttm = Column(Float, comment="市盈率 TTM")
    pb = Column(Float, comment="市净率")
    ps_ttm = Column(Float, comment="市销率 TTM")
    dividend_yield = Column(Float, comment="股息率 (%)")

    # 审计意见（关键红线）
    audit_opinion = Column(String(100), comment="审计意见")

    # 数据质量与来源
    data_source = Column(String(50), comment="数据来源，如 akshare/mock")
    data_freshness = Column(DateTime, comment="数据更新时间")
    completeness_score = Column(Float, comment="字段完整度 0-1")
    data_source_note = Column(Text, comment="字段来源与估算说明")

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
    stability_score = Column(Float, comment="增长稳定分")
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
    stability_score = Column(Float)
    pe_ttm = Column(Float)
    pb = Column(Float)
    roe = Column(Float)
    debt_to_asset = Column(Float)
    dividend_yield = Column(Float)
    data_json = Column(Text, comment="该日完整数据 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)


class UpdateLog(Base):
    """数据更新日志。"""
    __tablename__ = "update_logs"

    id = Column(Integer, primary_key=True)
    update_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), comment="success / partial / failed")
    message = Column(Text)
    stocks_count = Column(Integer)
    provider = Column(String(50), comment="使用的数据源")
    completeness_avg = Column(Float, comment="平均字段完整度")


class StockPrice(Base):
    """历史日线行情（后复权），用于回测。"""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), index=True, comment="股票代码")
    trade_date = Column(String(20), index=True, comment="交易日期 YYYYMMDD")
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    adj_open = Column(Float, comment="后复权开盘价")
    adj_close = Column(Float, comment="后复权收盘价")
    volume = Column(Float)
    source = Column(String(50), default="tushare", comment="数据来源")

    # ponytail: 简单防止重复写入，生产数据清洗后再加唯一约束


class AppConfig(Base):
    """应用配置表（前端设置页面可编辑）。"""
    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, comment="配置键")
    value = Column(Text, comment="配置值（JSON 字符串）")
    description = Column(String(255), comment="配置说明")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Portfolio(Base):
    """实盘推荐组合快照。"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_date = Column(String(20), index=True, comment="组合日期 YYYY-MM-DD")
    symbol = Column(String(20), index=True, comment="股票代码")
    name = Column(String(100))
    industry = Column(String(100))
    total_score = Column(Float)
    weight = Column(Float, comment="等权权重")
    data_json = Column(Text, comment="该日完整数据 JSON")
    created_at = Column(DateTime, default=datetime.utcnow)


class PortfolioNav(Base):
    """实盘组合每日净值。"""
    __tablename__ = "portfolio_navs"

    id = Column(Integer, primary_key=True, index=True)
    nav_date = Column(String(20), index=True, comment="净值日期 YYYY-MM-DD")
    portfolio_return = Column(Float, comment="组合累计收益（从组合成立起）")
    benchmark_return = Column(Float, comment="沪深300累计收益（从组合成立起）")
    daily_return = Column(Float, comment="当日收益")
    benchmark_daily_return = Column(Float, comment="沪深300当日收益")
    created_at = Column(DateTime, default=datetime.utcnow)
