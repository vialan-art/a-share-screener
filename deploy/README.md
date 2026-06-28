# A-Share Screener 部署指南

## 域名

`pizarro.vvnalnlgs.top`

## 服务器要求

- 已安装 Docker & Docker Compose
- 已配置域名解析到服务器 IP

## 部署步骤

### 1. 上传代码到服务器

```bash
# 在本地打包
git archive --format=tar.gz -o screener.tar.gz HEAD

# 上传到服务器
scp screener.tar.gz root@your-server-ip:/opt/

# 在服务器上解压
ssh root@your-server-ip
mkdir -p /opt/a-share-screener
cd /opt/a-share-screener
tar xzf /opt/screener.tar.gz
```

### 2. 配置环境变量

```bash
cd /opt/a-share-screener/backend
cp .env.example .env
nano .env
```

至少确认：

```env
AI_ADVISOR_ENABLED=false
# 如需启用 AI 顾问：
# AI_ADVISOR_API_KEY=sk-...
```

### 3. 启动服务

```bash
cd /opt/a-share-screener/deploy
docker-compose up -d --build
```

### 4. 验证

- 网站：http://pizarro.vvnalnlgs.top
- API 文档：http://pizarro.vvnalnlgs.top/api/v1/health

### 5. 首次运行选股

```bash
curl -X POST http://pizarro.vvnalnlgs.top/api/v1/run
```

或在 Dashboard 点击"手动运行选股"。

## HTTPS 配置（推荐）

使用 Caddy 自动 HTTPS：

```bash
# 安装 Caddy
docker run -d --name caddy \
  -p 80:80 -p 443:443 \
  -v /opt/a-share-screener/deploy/Caddyfile:/etc/caddy/Caddyfile \
  -v caddy_data:/data -v caddy_config:/config \
  caddy:2
```

`Caddyfile`：

```
pizarro.vvnalnlgs.top {
    reverse_proxy frontend:80
}
```

## 常用命令

```bash
# 查看日志
docker-compose logs -f backend
docker-compose logs -f frontend

# 重启
docker-compose restart

# 更新代码后重建
docker-compose up -d --build

# 进入后端容器
docker exec -it screener-backend bash
```

## 数据备份

数据库文件在 `/opt/a-share-screener/data/screener.db`，建议定期备份：

```bash
rsync -avz /opt/a-share-screener/data/ /backup/screener-data/
```
