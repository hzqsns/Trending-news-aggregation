import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc

from app.ai.client import chat_completion
from app.crawlers.manager import CrawlerManager
from app.database import async_session
from app.models.article import Article
from app.models.report import DailyReport
from app.platform.scheduler import SchedulerKernel
from app.skills.engine import run_importance_scoring
from app.sources.base import NewsItem
from app.agents.tech_info.defaults import CRAWLER_KEYS

logger = logging.getLogger(__name__)

AGENT_KEY = "tech_info"


async def _save_tech_items(items: list[NewsItem]) -> int:
    saved = 0
    async with async_session() as session:
        for item in items:
            if not item.title or not item.url:
                continue
            existing = await session.execute(
                select(Article).where(Article.agent_key == AGENT_KEY, Article.url == item.url)
            )
            if existing.scalar_one_or_none():
                continue
            article = Article(
                agent_key=AGENT_KEY,
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


async def job_fetch_tech():
    logger.info("⏰ Running tech info fetch")
    try:
        mgr = CrawlerManager(CRAWLER_KEYS)
        items, stats = await mgr.fetch_all()
        saved = await _save_tech_items(items)
        logger.info(f"Tech fetch: {stats['total_fetched']} fetched, {saved} saved")
        if saved > 0:
            await run_importance_scoring(agent_key="tech_info")
    except Exception as e:
        logger.error(f"Tech fetch job error: {e}")


def register_tech_jobs(kernel: SchedulerKernel) -> None:
    kernel.add_agent_job("tech_info", "fetch_tech", job_fetch_tech, "interval", minutes=30)


__all__ = ["register_tech_jobs", "job_fetch_tech"]
