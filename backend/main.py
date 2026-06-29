"""FastAPI 应用入口。"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import router
from backend.database.connection import engine, Base, init_db
from backend.core.config import get_settings

settings = get_settings()

# 创建所有数据库表
init_db()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="A股选股研究系统 API",
)

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应改成你的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "A-Share Screener API", "docs": "/docs"}
