---
title: AkShare 数据完整性提升
type: note
permalink: a-share-screener/project-log/ak-share-数据完整性提升
tags:
- akshare
- data-quality
- deploy
---

## 完成
- 改写 `backend/data/akshare_provider.py`：
  - `get_stock_list` 增加新浪 spot 回退，避免深交所接口超时导致 pipeline 失败。
  - `get_financial_metrics` 用 净利润/每股收益 反推总股本，从而摆脱对东方财富 spot 总市值的强依赖。
  - 由最新价和每股指标直接计算 PE/PB/PS，EM spot 不可用时仍可获得估值数据。
  - 新增新浪 spot 回退用于 `get_daily_prices`，并过滤 None 值避免覆盖财务指标。
  - 加载 `static_industry_map.json` 与 `static_sector_map.json` 作为行业/板块 fallback。
  - 使用业绩快报的 `所处行业` 覆盖静态行业映射。
- 更新 `backend/pipeline.py`：过滤前用财务指标中的行业覆盖股票列表里的静态行业。
- 部署到 VPS 并触发 `/api/v1/run`。

## 结果
- 生产环境 completeness 从 29.2% 提升到 64.4%。
- 500 只股票中 107 只通过过滤（此前 131）。
- `/snapshot/latest` 与 `/portfolio/latest` 均正常返回，行业标签更准确。

## 仍待解决
- 回测仍只有 1 个周期，需要累积更多历史快照。
- Portfolio NAV 需要至少两个交易日价格才能绘制曲线。
- 负债率使用默认值 45%，可后续接入真实财报负债数据。
- 新浪 spot 缺少换手率，动量分默认 0.5；EM spot 恢复后可自动改善。

## 2026-07-06 后续进展
- 接入真实资产负债表：`akshare_provider.py` 使用 Sina `stock_financial_report_sina` 获取 `debt_to_asset` 和 `total_assets`，替换 45% 默认负债率。
- 增加换手率 fallback：EM spot 不可用时，用 Sina 日线计算 20 日平均换手率。
- 滚动回测增强：
  - `backend/backtest/rolling.py` 支持 `monthly/weekly/daily/auto` 频率；`auto` 会按快照密度降级。
  - 日频回测 HTTPS 504 修复：新增 `PriceService.warm_cache_for_all_snapshots()` 为所有历史快照的 Top N 预热价格；`RollingBacktest.run()` 自动将 `end_date` 限制到本地缓存最新交易日，避免查询未来无价格日期触发外部拉取。
  - 回测时间过短（日频 <20 期、周频 <6 期、月频 <3 期）时，年化收益与夏普返回 `null`，避免误导性数字。
- 前端 `RollingBacktest.tsx`：增加频率选择器（自动/月度/周度/日度），默认日频；展示实际可用数据截止日期。
- 增加单元测试：`backend/tests/test_filters.py`、`test_scoring.py`、`test_rolling_backtest.py`，全部通过。
- 触发并完成了生产 `/api/v1/run`：500 只股票中 130 只通过，completeness 64.63%。

## 当前状态
- 日频滚动回测已可通过 HTTPS 正常返回：4 个周期（2026-06-29 至 2026-07-03），策略累计收益 +3.47%，沪深300 -1.72%。
- Portfolio / NAV：组合已更新至 2026-07-06；NAV 仍至 2026-07-05，待 19:00 定时任务根据新持仓更新。
- 价格缓存最新日期为 20260703，因此回测终点被限制在 2026-07-03；待明日数据更新后可自动扩展周期数。

## 仍待解决
- 自动模式下目前仍只有 1 个月度周期，需要积累更长时间序列后才会变成多期月度结果。
- 新浪/EM 网络不稳定时，股票列表拉取仍可能耗时数分钟（本次生产运行约 494 秒）。
- NAV 在组合日期突变时不会自动重算历史，可后续优化。