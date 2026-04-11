"""Shared fixtures for backend tests."""
import asyncio
import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key"

from app.database import Base  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session():
    """Provide a clean async DB session with all tables created."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Import all models so Base.metadata has them
    from app.models.user import User  # noqa: F401
    from app.models.article import Article  # noqa: F401
    from app.models.alert import Alert  # noqa: F401
    from app.models.report import DailyReport  # noqa: F401
    from app.models.skill import Skill  # noqa: F401
    from app.models.sentiment import SentimentSnapshot  # noqa: F401
    from app.models.setting import SystemSetting  # noqa: F401
    from app.models.bookmark import ArticleBookmark  # noqa: F401
    from app.models.calendar_event import CalendarEvent  # noqa: F401
    from app.models.macro_indicator import MacroDataPoint  # noqa: F401
    from app.models.historical_event import HistoricalEvent  # noqa: F401
    from app.models.cs2_item import CS2Item  # noqa: F401
    from app.models.cs2_price import CS2PriceSnapshot  # noqa: F401
    from app.models.cs2_prediction import CS2Prediction  # noqa: F401
    from app.models.cs2_watchlist import CS2Watchlist  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
