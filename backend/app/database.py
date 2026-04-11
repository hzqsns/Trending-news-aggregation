import json
import logging
import os

from sqlalchemy import TypeDecorator, Text, event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

logger = logging.getLogger(__name__)

from app.config import settings

db_url = settings.DATABASE_URL
db_path = db_url.replace("sqlite+aiosqlite:///", "")
db_dir = os.path.dirname(db_path)
if db_dir and db_dir != ".":
    os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(db_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def _configure_sqlite_connection(dbapi_connection, _connection_record):
    if not db_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA busy_timeout=5000;")
    cursor.close()


class Base(DeclarativeBase):
    pass


class JSONField(TypeDecorator):
    """SQLite-compatible JSON field."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value, ensure_ascii=False)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


async def init_db():
    from app.models.user import User  # noqa: F401
    from app.models.article import Article  # noqa: F401
    from app.models.alert import Alert  # noqa: F401
    from app.models.report import DailyReport  # noqa: F401
    from app.models.skill import Skill  # noqa: F401
    from app.models.sentiment import SentimentSnapshot  # noqa: F401
    from app.models.setting import SystemSetting  # noqa: F401
    from app.models.bookmark import ArticleBookmark  # noqa: F401
    from app.models.cs2_item import CS2Item  # noqa: F401
    from app.models.cs2_price import CS2PriceSnapshot  # noqa: F401
    from app.models.cs2_prediction import CS2Prediction  # noqa: F401
    from app.models.cs2_watchlist import CS2Watchlist  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_agent_key()


_AGENT_KEY_TABLES = {
    "articles": "investment",
    "daily_reports": "investment",
    "alerts": "investment",
    "skills": "investment",
    "sentiment_snapshots": "investment",
    "system_settings": None,  # NULL = global
}


async def _migrate_agent_key():
    """Add agent_key column to existing tables if missing (idempotent)."""
    async with engine.begin() as conn:
        for table, default_val in _AGENT_KEY_TABLES.items():
            cols = await conn.execute(text(f"PRAGMA table_info({table})"))
            col_names = [row[1] for row in cols.fetchall()]
            if "agent_key" in col_names:
                continue
            if default_val is not None:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN agent_key VARCHAR(50) DEFAULT '{default_val}' NOT NULL"
                ))
                logger.info(f"Migration: added agent_key to {table} (default='{default_val}')")
            else:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN agent_key VARCHAR(50) DEFAULT NULL"
                ))
                logger.info(f"Migration: added agent_key to {table} (nullable)")
