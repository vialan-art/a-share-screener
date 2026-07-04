---
title: 09-用FastAPI做后端
type: note
permalink: a-share-screener/docs/lessons/09-用-fast-api-做后端
---

# 第 9 课：用 FastAPI 做后端

## 什么是后端？

后端就是"服务器端的程序"，负责：

- 接收前端的请求
- 处理数据
- 返回结果

可以理解为餐厅里的厨房：顾客（前端）点菜，厨房（后端）做菜。

## FastAPI 是什么？

FastAPI 是 Python 的一个现代 Web 框架，特点是：

- 速度快
- 自动生成 API 文档
- 类型提示友好

## 最小示例

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/hello")
def hello():
    return {"message": "Hello, Screener!"}
```

运行：

```bash
uvicorn main:app --reload
```

访问：http://localhost:8000/hello

## API 文档

FastAPI 会自动生成文档：

- Swagger UI：http://localhost:8000/docs
- ReDoc：http://localhost:8000/redoc

## 路由

路由就是 URL 和处理函数的对应关系。

```python
@app.get("/api/v1/stocks")
def list_stocks():
    return [{"symbol": "000001", "name": "平安银行"}]
```

## 项目实战

`backend/api/routes.py` 里定义了所有 API：

- `POST /api/v1/run`：运行选股
- `GET /api/v1/snapshot/latest`：最新结果
- `GET /api/v1/export/watchlist`：导出 CSV
- `POST /api/v1/advisor/chat`：AI 顾问

## 小练习

1. 启动后端，访问 http://localhost:8000/docs 看看 API 文档。
2. 尝试调用 `/api/v1/health` 接口。

## 前后端如何通信？

前端通过 HTTP 请求调用后端 API。例如：

```javascript
const res = await fetch('/api/v1/snapshot/latest')
const data = await res.json()
```