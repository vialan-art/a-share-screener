# A-Share Screener

A股选股研究系统 —— 数据驱动、可扩展、教学友好。

> 目标：**辅助学习投资**，不是替代你做投资决策。

## 项目定位

这是一个"投研操作系统"的最小可行版本（MVP）：

- 自动采集 A 股财务和行情数据
- 用可配置的及格线过滤劣质公司
- 用多因子模型给股票打分
- 提供网页 Dashboard 查看结果
- 每日自动存档，支持历史对比
- 内置 AI 投资学习顾问

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python + FastAPI + SQLAlchemy + SQLite |
| 数据源 | AkShare（免费，可替换） |
| 前端 | React + TypeScript + Tailwind CSS + Vite |
| 定时任务 | schedule |
| 部署 | Docker + Docker Compose |

## 快速开始

### 1. 安装依赖

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 前端
cd ../frontend
npm install
```

### 2. 配置环境变量

```bash
cd backend
cp .env.example .env
# 编辑 .env，填入你的 AI 顾问 API Key（可选）
```

### 3. 启动后端

```bash
cd backend
uvicorn backend.main:app --reload
```

访问 API 文档：http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend
npm run dev
```

访问 Dashboard：http://localhost:5173

### 5. 首次运行选股

在 Dashboard 点击"手动运行选股"，或调用 API：

```bash
curl -X POST http://localhost:8000/api/v1/run
```

## 目录结构

```
a-share-screener/
├── backend/
│   ├── api/            API 路由
│   ├── core/           配置
│   ├── data/           数据源接口和 AkShare 实现
│   ├── database/       数据库模型和连接
│   ├── filters/        及格线过滤引擎
│   ├── scoring/        多因子评分引擎
│   ├── advisor/        AI 顾问服务
│   ├── scheduler/      定时任务
│   └── main.py         FastAPI 入口
├── frontend/           React Dashboard
├── docs/lessons/       Python & 投资知识点讲义
└── deploy/             Docker 部署配置
```

## 数据流程

```
AkShare
  │
  ▼
股票列表 / 财务指标 / 行情数据
  │
  ▼
过滤引擎（审计意见、ROE、负债率、现金流...）
  │
  ▼
评分引擎（质量、估值、动量）
  │
  ▼
SQLite 数据库 + 每日快照
  │
  ▼
Dashboard / CSV Watchlist / AI 顾问
```

## AI 顾问配置

在 `backend/.env` 中设置：

```env
AI_ADVISOR_ENABLED=true
AI_ADVISOR_API_URL=https://api.openai.com/v1/chat/completions
AI_ADVISOR_API_KEY=sk-...
AI_ADVISOR_MODEL=gpt-4o-mini
AI_ADVISOR_TEMPERATURE=0.7
```

兼容任何 OpenAI 格式的 API，包括自定义代理。

## 免责声明

本程序仅用于学习和研究，不构成任何投资建议。股市有风险，投资需谨慎。

## License

MIT
