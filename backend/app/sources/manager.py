import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.article import Article
from app.models.setting import SystemSetting
from app.sources.base import NewsItem, NewsSource
from app.sources.rss import RSSSource
from app.sources.crypto import CryptoSource

logger = logging.getLogger(__name__)

ALL_SOURCES: list[NewsSource] = [
    RSSSource(),
    CryptoSource(),
]


async def _is_source_enabled(session: AsyncSession, key: str) -> bool:
    if not key:
        return True
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        return True
    return setting.value == "true"


async def _save_items(session: AsyncSession, items: list[NewsItem]) -> int:
    saved = 0
    for item in items:
        if not item.title or not item.url:
            continue
        existing = await session.execute(
            select(Article).where(Article.url == item.url)
        )
        if existing.scalar_one_or_none():
            continue

        article = Article(
            title=item.title,
            url=item.url,
            source=item.source,
            category=item.category,
            summary=item.summary,
            content=item.content,
            image_url=item.image_url,
            published_at=item.published_at,
            fetched_at=datetime.utcnow(),
            importance=item.importance,
        )
        session.add(article)
        saved += 1

    if saved > 0:
        await session.commit()
    return saved


async def fetch_all_sources() -> dict:
    """Run all enabled sources and save results."""
    stats = {"total_fetched": 0, "total_saved": 0, "sources": {}}

    async with async_session() as session:
        tasks = []
        enabled_sources = []
        for source in ALL_SOURCES:
            if await _is_source_enabled(session, source.enabled_key):
                tasks.append(source.fetch())
                enabled_sources.append(source)

        if not tasks:
            logger.info("No enabled sources")
            return stats

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items = []
        for source, result in zip(enabled_sources, results):
            if isinstance(result, Exception):
                logger.error(f"Source {source.name} failed: {result}")
                stats["sources"][source.name] = {"error": str(result)}
                continue

            stats["sources"][source.name] = {"fetched": len(result)}
            stats["total_fetched"] += len(result)
            all_items.extend(result)

        saved = await _save_items(session, all_items)
        stats["total_saved"] = saved

    logger.info(f"Fetch complete: {stats['total_fetched']} fetched, {saved} new")
    return stats
