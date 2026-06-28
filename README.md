# A-Share Screener

一个面向 A 股投资者的**研究型选股系统**。

在线地址：https://pizarro.vvnalnlgs.top

> 目标：用数据整理和量化呈现辅助投资学习，**不做买卖预测，不替代投资决策**。

---

## 一、项目定位与目标

本系统是一个"投研操作系统"的最小可行版本（MVP）。

对投资初学者来说，最大的痛点不是"没有数据"，而是：

- 数据太散，无法快速对比
- 财务指标概念复杂，难以建立直觉
- 不知道哪些公司是"明显不能碰"的
- 缺乏对研究过程的记录和复盘

因此，本系统的核心目标是：

1. **整理信息**：把股票基本面、估值、动量数据结构化
2. **量化呈现**：用打分和可视化建立对公司的直观认知
3. **排除风险**：通过可配置的及格线过滤掉有硬伤的公司
4. **辅助学习**：内置 AI 顾问，随时解释投资概念
5. **记录过程**：每日自动存档，支持历史对比

---

## 二、当前功能

### 数据层

- A 股股票列表、行情数据、财务指标采集
- 默认使用 **AkShare**（免费），内置 **Mock 数据源**用于稳定演示
- 数据源接口可插拔，未来可替换为 Tushare、Wind、Bloomberg 等

### 过滤层

- 审计意见红线（只保留标准无保留意见）
- 行业差异化及格线（银行/保险/房地产等重资产行业放宽负债率要求）
- ROE、资产负债率、净利润增长、经营现金流等基础指标
- 过滤不通过会记录具体原因

### 评分层

- 三维度多因子打分：质量（45%）、估值（35%）、动量（20%）
- 使用百分位排名进行标准化，避免量纲差异
- 权重可在代码中调整，未来支持 UI 配置

### 可视化层

- 系统概览：快照日期、候选数量、最高分、更新状态
- 今日优选：TOP 股票列表与得分拆解
- 行业分布：候选股票的行业集中度
- 候选股票池：支持行业筛选、最低得分筛选、多维度排序
- 股票详情：雷达图 + 关键财务指标卡片
- 历史存档：每日快照对比
- 运行日志：数据更新状态追踪
- AI 顾问：OpenAI 兼容接口，可解释指标和选股逻辑

### 输出

- 导出 TradingView watchlist CSV
- 每日 19:00 自动运行并存档

---

## 三、技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                            │
│  React + TypeScript + Tailwind CSS + Framer Motion          │
│  Recharts 可视化                                              │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP / REST
┌───────────────────────────▼─────────────────────────────────┐
│                         Backend                             │
│  FastAPI + SQLAlchemy + SQLite + Pydantic                   │
│  数据源接口可插拔（AkShare / Mock / 未来其他）                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                       Data Sources                          │
│  AkShare（免费） / Mock（演示） / Tushare / Wind（未来）       │
└─────────────────────────────────────────────────────────────┘
```

### 目录结构

```
a-share-screener/
├── backend/
│   ├── api/              # FastAPI 路由
│   ├── core/             # 配置管理
│   ├── data/             # 数据源接口与实现
│   │   ├── provider.py       # 抽象接口
│   │   ├── akshare_provider.py
│   │   ├── mock_provider.py
│   │   └── factory.py
│   ├── database/         # 数据库模型与连接
│   ├── filters/          # 及格线过滤引擎
│   ├── scoring/          # 多因子评分引擎
│   ├── advisor/          # AI 顾问服务
│   ├── scheduler/        # 定时任务
│   └── main.py           # FastAPI 入口
├── frontend/             # React Dashboard
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── index.css
│   └── package.json
├── deploy/               # Docker 部署配置
├── docs/lessons/         # Python & 投资知识点讲义
└── README.md
```

---

## 四、本地运行

### 1. 克隆项目

```bash
git clone https://github.com/vialan-art/a-share-screener.git
cd a-share-screener
```

### 2. 启动后端

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 复制环境变量配置
cp .env.example .env

# 启动服务
PYTHONPATH=.. uvicorn backend.main:app --reload
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### 4. 首次运行选股

在 Dashboard 点击"运行选股"，或调用 API：

```bash
curl -X POST http://localhost:8000/api/v1/run
```

---

## 五、部署到 VPS

详见 [deploy/README.md](deploy/README.md)。

简版命令：

```bash
cd deploy
docker-compose up -d --build
```

---

## 六、AI 顾问配置

在 `backend/.env` 中设置：

```env
AI_ADVISOR_ENABLED=true
AI_ADVISOR_API_URL=https://api.openai.com/v1/chat/completions
AI_ADVISOR_API_KEY=sk-...
AI_ADVISOR_MODEL=gpt-4o-mini
AI_ADVISOR_TEMPERATURE=0.7
```

兼容任何 OpenAI 格式的 API，包括自定义代理。

---

## 七、教学讲义

`docs/lessons/` 目录下有适合初学者的讲义：

1. 为什么用 Python
2. 变量和类型
3. 列表和字典
4. Pandas 表格入门
5. 从 AkShare 拿数据
6. ROE / PE / PB 是什么
7. Z-score 标准化
8. 多因子打分
9. 用 FastAPI 做后端
10. 前端怎么显示表格
11. Docker 部署

---

## 八、未来可优化方向

本项目采用"持续演进"策略，以下是明确可扩展的方向：

### 短期（1-2 周）

- [ ] 在 Dashboard 上直接调整评分权重和及格线
- [ ] 增加更多财务指标（自由现金流、研发费用、资本支出等）
- [ ] 股票详情页嵌入 TradingView K 线图
- [ ] 添加估值历史分位数图表
- [ ] 改进 AkShare 数据拉取的稳定性和速度

### 中期（1-3 个月）

- [ ] 接入真实财报 PDF，扫描审计意见关键词
- [ ] 增加港股、美股数据源
- [ ] 构建自选股组合和风险集中度分析
- [ ] 回测实验室：验证筛选条件的历史表现
- [ ] 决策日志系统：记录买入/卖出理由并复盘

### 长期（6-12 个月）

- [ ] 多 Agent 协同研究（公司分析、财报分析、风险监控、学习助教）
- [ ] 知识图谱：公司、行业、供应链关系
- [ ] 自动投资笔记生成并同步到 Obsidian
- [ ] 文档知识库 RAG：支持对年报、书籍全文检索
- [ ] 从 SQLite 迁移到 PostgreSQL

---

## 九、已知问题

1. **AkShare 网络不稳定**：本项目默认使用 Mock 数据源保证演示稳定，生产环境可切换到 AkShare。
2. **行业分类不够精确**：AkShare 返回的行业字段在某些接口中为空，需要补充更可靠的行业数据源。
3. **评分权重固定**：目前需要在代码中调整，UI 配置尚未实现。
4. **缺少实时行情**：动量分基于当日行情，非高频数据。

---

## 十、免责声明

本程序仅用于学习和研究，不构成任何投资建议。股市有风险，投资需谨慎。

所有数据均来自第三方公开接口，其准确性和完整性请自行判断。

---

## License

MIT
