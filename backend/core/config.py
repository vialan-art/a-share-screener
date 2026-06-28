from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置。

    这些值会优先从环境变量读取，如果没有则使用默认值。
    比如 DATABASE_URL 环境变量会覆盖下面的默认值。
    """

    app_name: str = "A-Share Screener"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    database_url: str = "sqlite:///./data/screener.db"

    ai_advisor_enabled: bool = False
    ai_advisor_api_url: str = "https://api.openai.com/v1/chat/completions"
    ai_advisor_api_key: str = ""
    ai_advisor_model: str = "gpt-4o-mini"
    ai_advisor_temperature: float = 0.7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """用 lru_cache 缓存配置，避免每次读取都重新解析环境变量。"""
    return Settings()
