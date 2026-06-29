"""数据库连接和模型基类。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.config import get_settings
import os

settings = get_settings()

# 确保数据库文件所在目录存在
db_path = settings.database_path
os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)

# SQLite 在 FastAPI 多线程下需要 check_same_thread=False
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

# SessionLocal 是创建数据库会话的工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 是所有模型（表）的基类
Base = declarative_base()


def init_db():
    """创建所有表。如果表结构变更，SQLite 需要手动迁移或重建数据库。"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖：每个请求创建一个数据库会话，请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
