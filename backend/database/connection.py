"""数据库连接和模型基类。"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from backend.core.config import get_settings

settings = get_settings()

# SQLite 在 FastAPI 多线程下需要 check_same_thread=False
# connect_args 只对 SQLite 有效，对其他数据库不会生效
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)

# SessionLocal 是创建数据库会话的工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 是所有模型（表）的基类
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每个请求创建一个数据库会话，请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
