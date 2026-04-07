import json
import os

from sqlalchemy import TypeDecorator, Text, event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

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

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
