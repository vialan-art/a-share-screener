# 第 5 课：从 AkShare 拿数据

## AkShare 是什么？

AkShare 是一个免费的开源 Python 库，专门用来获取中国金融数据（A股、港股、期货、基金等）。

它不需要注册 API Key，底层是从东方财富、新浪财经等网站抓取公开数据。

## 安装

```bash
pip install akshare
```

## 获取股票列表

```python
import akshare as ak

# A股所有股票代码和名称
df = ak.stock_info_a_code_name()
print(df.head())
```

## 获取实时行情

```python
df = ak.stock_zh_a_spot_em()
print(df[["代码", "名称", "最新价", "涨跌幅", "市盈率-动态", "市净率"]].head())
```

## 获取财务指标

```python
# 某只股票的主要财务指标
df = ak.stock_financial_analysis_indicator(symbol="000001")
print(df.head())
```

## 为什么需要封装？

AkShare 的接口经常变化，而且返回的列名不太稳定。如果我们的程序直接调用 AkShare，一旦接口变了就要改很多地方。

所以我们做了一个**数据提供者接口**（`backend/data/provider.py`），把 AkShare 包在里面：

```python
class DataProvider(ABC):
    @abstractmethod
    def get_stock_list(self):
        pass
```

以后换 Tushare、Wind、Bloomberg 时，只需要写一个新的 Provider 实现这个接口，业务逻辑完全不用改。

## 小练习

1. 安装 AkShare，尝试获取股票列表并打印前 10 行。
2. 查询 "贵州茅台"（600519）的财务指标。

## 注意事项

- AkShare 依赖网络，如果请求失败可能是被限流，可以降低请求频率。
- 数据仅供学习研究使用。
- 有些接口在非交易时间会慢或不可用。
