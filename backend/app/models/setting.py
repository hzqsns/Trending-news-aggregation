from datetime import datetime

from sqlalchemy import String, Text, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SystemSetting(Base):
    """Web 可配置化的系统设置，存储在数据库中。"""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="general")
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(String(20), default="text")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "key": self.key,
            "value": self.value,
            "category": self.category,
            "label": self.label,
            "description": self.description,
            "field_type": self.field_type,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


DEFAULT_SETTINGS = [
    # --- 系统配置 ---
    {"key": "fetch_interval", "value": "15", "category": "system", "label": "采集间隔（分钟）", "description": "新闻源采集的时间间隔", "field_type": "number"},
    {"key": "timezone", "value": "Asia/Shanghai", "category": "system", "label": "时区", "description": "系统使用的时区", "field_type": "text"},
    # --- AI 配置 ---
    {"key": "ai_enabled", "value": "true", "category": "ai", "label": "启用 AI 分析", "description": "是否启用 AI 驱动的新闻分析和评分", "field_type": "boolean"},
    {"key": "ai_api_key", "value": "", "category": "ai", "label": "AI API Key", "description": "OpenAI 兼容接口的 API Key", "field_type": "password"},
    {"key": "ai_api_base", "value": "https://api.openai.com/v1", "category": "ai", "label": "AI API Base URL", "description": "可替换为 DeepSeek 等兼容接口地址", "field_type": "text"},
    {"key": "ai_model", "value": "gpt-4o-mini", "category": "ai", "label": "AI 模型", "description": "使用的模型名称（gpt-4o-mini / deepseek-chat 等）", "field_type": "text"},
    # --- 数据源配置 ---
    {"key": "source_rss_enabled", "value": "true", "category": "sources", "label": "启用 RSS 源", "description": "从财经 RSS 源采集新闻", "field_type": "boolean"},
    {"key": "source_rss_feeds", "value": "[]", "category": "sources", "label": "RSS 源列表", "description": "JSON 格式的 RSS 源配置", "field_type": "json"},
    {"key": "source_crypto_enabled", "value": "true", "category": "sources", "label": "启用加密货币新闻", "description": "从 CoinGecko 等采集加密货币资讯", "field_type": "boolean"},
    {"key": "source_newsapi_enabled", "value": "false", "category": "sources", "label": "启用 NewsAPI", "description": "从 NewsAPI 采集国际财经新闻", "field_type": "boolean"},
    {"key": "source_newsapi_key", "value": "", "category": "sources", "label": "NewsAPI Key", "description": "NewsAPI.org 的 API Key", "field_type": "password"},
    # --- Telegram 配置 ---
    {"key": "telegram_enabled", "value": "false", "category": "notifications", "label": "启用 Telegram 推送", "description": "通过 Telegram Bot 推送新闻和预警", "field_type": "boolean"},
    {"key": "telegram_bot_token", "value": "", "category": "notifications", "label": "Telegram Bot Token", "description": "从 @BotFather 获取的 Bot Token", "field_type": "password"},
    {"key": "telegram_chat_id", "value": "", "category": "notifications", "label": "Telegram Chat ID", "description": "推送目标的 Chat ID", "field_type": "text"},
    # --- 微信配置 ---
    {"key": "wechat_enabled", "value": "false", "category": "notifications", "label": "启用微信推送", "description": "通过 PushPlus 推送到微信", "field_type": "boolean"},
    {"key": "pushplus_token", "value": "", "category": "notifications", "label": "PushPlus Token", "description": "从 pushplus.plus 获取的 Token", "field_type": "password"},
    # --- QQ 配置 ---
    {"key": "qq_enabled", "value": "false", "category": "notifications", "label": "启用 QQ 推送", "description": "通过 Qmsg 推送到 QQ", "field_type": "boolean"},
    {"key": "qmsg_key", "value": "", "category": "notifications", "label": "Qmsg Key", "description": "从 qmsg.zendee.cn 获取的 Key", "field_type": "password"},
    # --- 推送策略 ---
    {"key": "push_important_immediately", "value": "true", "category": "push_strategy", "label": "重要新闻立即推送", "description": "重要度 >= 3 的新闻立即推送", "field_type": "boolean"},
    {"key": "push_digest_interval", "value": "30", "category": "push_strategy", "label": "摘要推送间隔（分钟）", "description": "汇总推送的时间间隔", "field_type": "number"},
    {"key": "push_morning_report", "value": "true", "category": "push_strategy", "label": "推送早间日报", "description": "每日 07:30 推送市场早报", "field_type": "boolean"},
    {"key": "push_evening_report", "value": "true", "category": "push_strategy", "label": "推送晚间日报", "description": "每日 22:00 推送市场晚报", "field_type": "boolean"},
]
