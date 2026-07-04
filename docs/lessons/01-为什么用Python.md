---
title: 01-为什么用Python
type: note
permalink: a-share-screener/docs/lessons/01-为什么用-python
---

# 第 1 课：为什么用 Python 做这个项目？

## 一句话总结

Python 是一门"写起来像伪代码"的语言，特别适合处理表格数据和自动化任务，对初学者非常友好。

## 比喻理解

想象你要做一道菜：

- **C/C++** 像从种地、养猪开始自己准备所有食材，性能极高但麻烦。
- **JavaScript** 像做甜点，主要给网页用。
- **Python** 像用半成品食材做菜，有人已经把切菜、洗菜做好了，你负责组合。

做投资研究系统，我们最关心的是**快速验证想法**，而不是追求极致性能。Python 正好合适。

## 本项目为什么选择 Python？

| 原因 | 解释 |
|------|------|
| 数据处理强 | pandas 库处理 Excel/CSV/数据库非常方便 |
| 财经数据接口多 | AkShare、Tushare、yfinance 都是 Python 库 |
| Web 后端方便 | FastAPI 几行代码就能提供 API |
| 数学工具全 | NumPy、SciPy、scikit-learn 等 |
| 学习曲线平缓 | 语法接近自然语言 |

## 第一个 Python 程序

在项目根目录运行：

```bash
python -c "print('Hello, Screener!')"
```

你会看到输出：

```
Hello, Screener!
```

## 小练习

1. 打开终端，输入上面的命令，确认 Python 已安装。
2. 试着把 `Screener` 改成你自己的名字。

## 在本项目中的位置

本项目的后端完全用 Python 写成。你不需要精通它，但要学会看懂和修改。