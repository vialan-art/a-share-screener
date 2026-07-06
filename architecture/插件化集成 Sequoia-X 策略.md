---
title: 插件化集成 Sequoia-X 策略
type: decision
permalink: a-share-screener/architecture/插件化集成-sequoia-x-策略
tags:
- plugins
- Sequoia-X
- RPS
- A股策略
- integration
---

## 决策
将 Sequoia-X 的 A 股特色策略以插件形式接入现有插件框架，不引入其 DataEngine/Settings/飞书推送。

## 新增内容
- `backend/plugins/sequoia_strategies.py`：6 个策略插件
  - `rps_breakout_120`：RPS 相对强度突破（需预计算 rps_120）
  - `limit_up_shakeout`：涨停洗盘
  - `uptrend_limit_down`：上升趋势放量跌停
  - `high_tight_flag`：高窄旗形整理
  - `ma_volume_golden_cross`：均线放量金叉
  - `turtle_trade_enhanced`：改良版海龟交易（20 日新高 + 成交额过亿 + 阳线 + 真涨）
- `backend/plugins/rps.py`：批量计算 RPS（全市场截面排名）
- `backend/plugins/adapter.py`：`enrich_batch` 自动调用 RPS 计算
- `backend/data/baostock_client.py`：返回 turnover 字段供策略使用
- `backend/plugins/data_service.py`：统一列名并传递 turnover
- `backend/tests/test_sequoia_plugins.py`：8 个单元测试

## 接入效果
- 插件总数从 15 个增至 21 个
- 真实数据评估：21/21 插件 100% 覆盖
- RPS 计算生效：8 只样本股有明确排名
- 全部单元测试通过：29 passed

## 相关文件
- `backend/plugins/sequoia_strategies.py`
- `backend/plugins/rps.py`
- `backend/plugins/adapter.py`
- `backend/data/baostock_client.py`
- `backend/plugins/data_service.py`
- `backend/tests/test_sequoia_plugins.py`