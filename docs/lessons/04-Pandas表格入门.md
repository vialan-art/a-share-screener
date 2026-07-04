---
title: 04-Pandas表格入门
type: note
permalink: a-share-screener/docs/lessons/04-pandas-表格入门
---

# 第 4 课：Pandas 表格入门

## Pandas 是什么？

Pandas 是 Python 里处理表格数据的库。你可以把它想象成 Excel 的 Python 版本。

```python
import pandas as pd

# 创建一个 DataFrame（数据框）
df = pd.DataFrame({
    "symbol": ["000001", "600519", "000858"],
    "name": ["平安银行", "贵州茅台", "五粮液"],
    "pe": [8.5, 28.5, 22.0],
    "roe": [10.0, 25.0, 18.0],
})

print(df)
```

输出：

```
   symbol name    pe   roe
0  000001  平安银行   8.5  10.0
1  600519  贵州茅台  28.5  25.0
2  000858   五粮液  22.0  18.0
```

## 常用操作

### 查看数据

```python
df.head()         # 前 5 行
df.tail()         # 后 5 行
df.info()         # 数据信息
df.describe()     # 统计摘要
```

### 筛选

```python
# 选出 PE < 15 的股票
cheap = df[df["pe"] < 15]
print(cheap)
```

### 排序

```python
# 按 ROE 降序排列
df_sorted = df.sort_values("roe", ascending=False)
```

### 计算新列

```python
df["score"] = df["roe"] / df["pe"]   # ROE/PE 比值
```

### 分组统计

```python
# 按行业计算平均 PE（假设有 industry 列）
industry_avg = df.groupby("industry")["pe"].mean()
```

## 读取和保存

```python
# 读取 CSV
df = pd.read_csv("stocks.csv")

# 保存 CSV
df.to_csv("output.csv", index=False)
```

## 小练习

1. 用上面的 DataFrame，筛选出 ROE > 15 的股票。
2. 按 PE 从小到大排序。
3. 新增一列 `value_score = roe / pe`。

## 项目实战

`backend/data/akshare_provider.py` 里大量使用了 Pandas：

```python
df = ak.stock_info_a_code_name()
for _, row in df.iterrows():
    symbol = str(row["code"]).strip()
```

这里 `iterrows()` 是逐行遍历 DataFrame 的方法。