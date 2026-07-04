"""运行时配置服务：数据库配置优先，环境变量兜底。"""
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal
from backend.database.models import AppConfig
from backend.core.config import get_settings


DEFAULTS = {
    "ai_base_url": "",
    "ai_api_key": "",
    "ai_model": "gpt-4o-mini",
    "data_provider": "mock",
    "max_stocks": "500",
    "scheduler_time": "19:00",
    "database_url": "",
    "market_region": "cn",
}


def get_config(key: str, default=None) -> str:
    """从数据库读取配置，无值则返回 default / 环境变量兜底。"""
    db: Session = SessionLocal()
    try:
        row = db.query(AppConfig).filter(AppConfig.key == key).first()
        if row and row.value:
            return row.value
    finally:
        db.close()

    if default is not None:
        return default

    # 兜底：部分键映射到 Settings / 环境变量
    settings = get_settings()
    env_fallback = {
        "ai_base_url": settings.ai_advisor_api_url,
        "ai_api_key": settings.ai_advisor_api_key,
        "ai_model": settings.ai_advisor_model,
        "data_provider": "mock",
        "max_stocks": "500",
    }
    return env_fallback.get(key, DEFAULTS.get(key, ""))


def get_provider_name() -> str:
    """获取当前应使用的数据源名称。"""
    import os
    return os.environ.get("SCREENER_PROVIDER") or get_config("data_provider", "mock")
