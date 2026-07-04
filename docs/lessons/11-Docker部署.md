---
title: 11-Docker部署
type: note
permalink: a-share-screener/docs/lessons/11-docker-部署
---

# 第 11 课：Docker 部署

## 什么是 Docker？

Docker 是一个"集装箱"工具，把你的程序和它需要的所有依赖打包在一起。

好处：

- 在本地能跑，在服务器上也能跑
- 不用在服务器上装一堆环境
- 一次构建，到处运行

## 三个核心概念

| 概念 | 比喻 | 说明 |
|------|------|------|
| **镜像** | 集装箱模板 | 程序的打包文件 |
| **容器** | 运行的集装箱 | 镜像的实例 |
| **Docker Compose** | 集装箱调度员 | 同时管理多个容器 |

## Dockerfile 示例

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0"]
```

## Docker Compose

`docker-compose.yml` 定义多个服务如何一起运行：

```yaml
services:
  backend:
    build: .
    ports:
      - "8000:8000"
  frontend:
    build: ./frontend
    ports:
      - "80:80"
```

启动：

```bash
docker-compose up -d --build
```

## 本项目的部署

详见 `deploy/README.md`。

## 常用命令

```bash
# 构建并启动
docker-compose up -d --build

# 查看日志
docker-compose logs -f

# 停止
docker-compose down

# 重启
docker-compose restart
```

## 小练习

1. 在本地安装 Docker。
2. 运行 `docker-compose up -d --build` 看看能不能启动。

## 为什么用 Docker？

对于本项目，Docker 让你可以把本地开发好的程序**原封不动**搬到 VPS 上，避免"我本地明明能跑"的尴尬。