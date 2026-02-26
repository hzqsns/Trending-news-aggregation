from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    JWT_SECRET: str = "change-me-to-a-random-secret-key"
    DEFAULT_ADMIN_USER: str = "admin"
    DEFAULT_ADMIN_PASS: str = "admin123"
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/news_agent.db"

    AI_API_KEY: Optional[str] = None
    AI_API_BASE: str = "https://api.openai.com/v1"
    AI_MODEL: str = "gpt-4o-mini"

    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    PUSHPLUS_TOKEN: Optional[str] = None
    QMSG_KEY: Optional[str] = None

    FRONTEND_URL: str = "http://localhost:5173"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
