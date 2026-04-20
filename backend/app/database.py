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

    await _fix_unique_constraints()


async def _fix_unique_constraints():
    """Fix old single-column UNIQUE → composite (agent_key, ...) UNIQUE.

    SQLite cannot ALTER CONSTRAINT, so we: create tmp → copy → drop → rename.
    Idempotent: skips if new composite index already exists.
    """
    migrations = {
        "articles": ("url", "uq_articles_agent_url", "agent_key, url"),
        "skills": ("slug", "uq_skills_agent_slug", "agent_key, slug"),
        "daily_reports": ("report_type, report_date", "uq_report_agent_type_date", "agent_key, report_type, report_date"),
        "system_settings": ("key", "uq_settings_agent_key", "agent_key, key"),
    }

    async with engine.begin() as conn:
        for table, (old_cols_str, new_idx_name, new_cols_str) in migrations.items():
            # Check if already migrated
            indexes = (await conn.execute(text(f"PRAGMA index_list({table})"))).fetchall()
            idx_names = [idx[1] for idx in indexes]
            if new_idx_name in idx_names:
                continue

            # Check old UNIQUE still present
            old_cols = [c.strip() for c in old_cols_str.split(",")]
            has_old = False
            for idx in indexes:
                if idx[2]:  # unique
                    cols = (await conn.execute(text(f'PRAGMA index_info("{idx[1]}")'))).fetchall()
                    if [c[2] for c in cols] == old_cols:
                        has_old = True
                        break

            if not has_old:
                continue

            logger.info(f"Migration: rebuilding {table} — UNIQUE({old_cols_str}) → UNIQUE({new_cols_str})")

            # Get all column info
            col_info = (await conn.execute(text(f"PRAGMA table_info({table})"))).fetchall()
            col_names = [r[1] for r in col_info]
            cols_csv = ", ".join(col_names)

            # Build new CREATE TABLE from ORM metadata
            sa_table = Base.metadata.tables.get(table)
            if sa_table is None:
                continue

            from sqlalchemy.schema import CreateTable
            create_ddl = str(CreateTable(sa_table).compile(conn.sync_engine))

            tmp = f"_migrate_{table}"
            await conn.execute(text(f"DROP TABLE IF EXISTS {tmp}"))

            # Replace table name in DDL
            tmp_ddl = create_ddl.replace(f"CREATE TABLE {table}", f"CREATE TABLE {tmp}", 1)
            await conn.execute(text(tmp_ddl))

            await conn.execute(text(f"INSERT INTO {tmp} ({cols_csv}) SELECT {cols_csv} FROM {table}"))
            await conn.execute(text(f"DROP TABLE {table}"))
            await conn.execute(text(f"ALTER TABLE {tmp} RENAME TO {table}"))

            logger.info(f"Migration: {table} rebuilt OK")
