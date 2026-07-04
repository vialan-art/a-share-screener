---
title: 07-Z-score标准化
type: note
permalink: a-share-screener/docs/lessons/07-z-score-标准化
---

# 第 7 课：Z-score 标准化

## 为什么要标准化？

假设你要同时比较两家公司的 ROE 和 PE：

| 公司 | ROE | PE |
|------|-----|-----|
| A | 20% | 30 |
| B | 10% | 15 |

ROE 是百分比，PE 是绝对数字，直接相加没有意义。

标准化就是把不同指标变成**同一尺度**（比如 0-1 之间），这样才可以比较和加权。

## 百分位排名

本项目用的是一种简单的标准化方法：**百分位排名**。

```
百分位 = （比它小的数值个数）/ （总个数）
```

例如 ROE = 20%，在 [5%, 10%, 15%, 20%, 25%] 中：

- 比 20% 小的有 3 个（5, 10, 15）
- 总共有 5 个
- 百分位 = 3/5 = 0.6

表示 ROE 超过了 60% 的公司。

## 越高越好 vs 越低越好

- ROE 越高越好 → 百分位直接就是分数
- PE 越低越好 → 用 1 - 百分位作为分数

## 代码实现

在 `backend/scoring/engine.py` 里：

```python
def _percentile_rank(self, value, values, higher_is_better=True):
    clean_values = [v for v in values if v is not None]
    n = len(clean_values)
    below = sum(1 for v in clean_values if v <= value)
    percentile = below / n

    if higher_is_better:
        return percentile
    else:
        return 1 - percentile
```

## 小练习

1. 数据集 [10, 20, 30, 40, 50]，计算 30 的百分位排名。
2. 为什么 PE 要用 `1 - 百分位`？

## 更高级的方法

除了百分位，还有：

- **Z-score**：`(x - 平均值) / 标准差`
- **Min-Max 归一化**：`(x - min) / (max - min)`

本项目先用百分位，因为它对异常值不敏感，更适合财务数据。