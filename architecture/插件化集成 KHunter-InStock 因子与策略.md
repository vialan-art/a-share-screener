---
title: 插件化集成 KHunter/InStock 因子与策略
type: decision
permalink: a-share-screener/architecture/插件化集成-khunter-in-stock-因子与策略
tags:
- plugins
- quant
- integration
- KHunter
- InStock
---

## 决策
将 KHunter 和 InStock 的计算层以插件形式集成到 A 股筛选器，而非完整搬运项目。

## 新增架构
- `backend/plugins/base.py`: `SignalPlugin` 协议 + `SignalResult`
- `backend/plugins/registry.py`: 全局插件注册表，支持类装饰器自动注册
- `backend/plugins/indicators.py`: 6 个技术指标插件（MACD/KDJ/RSI/BOLL/MA 多头/ATR）
- `backend/plugins/patterns.py`: 4 个 K 线形态插件（锤子线/吞没/十字星/早晨之星）
- `backend/plugins/strategies.py`: 5 个选股策略插件（放量上涨/平台突破/海龟突破/低波动成长/回踩年线）
- `backend/plugins/adapter.py`: 插件信号 enrich 到现有 metrics
- `backend/plugins/data_service.py`: 为插件批量获取 OHLCV，兼容 BaoStock/Tushare 列名

## 接入点
- `ScoringEngine` 增加 `technical_weight`（默认 10%），聚合插件技术面分数
- `ScreenerPipeline` 在过滤后、评分前，为通过股票补充 K 线和技术面信号

## 效果
- 8 只样本股票 14/15 插件 100% 覆盖；仅回踩年线因需 250 日数据，在短期样本中未触发
- 全部单元测试通过（21 passed）
- 无新增系统依赖（无 TA-Lib/Playwright）

## 下一步候选
- Hikyuu: 高性能 A 股回测/指标库（Apache-2.0）
- Sequoia-X: 涨跌停/RPS/海龟等 A 股策略（MIT）
- stock-scanner: AI + 情绪分析 + 25 财务指标（MIT）
- czsc / chan.py: 缠论技术分析

## 相关文件
- `backend/plugins/`
- `backend/scoring/engine.py`
- `backend/pipeline.py`
- `backend/scripts/evaluate_plugins.py`
- `backend/tests/test_plugins.py`
- `backend/tests/test_pipeline_plugins.py`