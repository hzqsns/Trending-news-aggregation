import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, delete

from app.database import async_session
from app.models.article import Article
from app.models.setting import SystemSetting
from app.sources.manager import fetch_all_sources
from app.skills.engine import run_importance_scoring, generate_daily_report, run_anomaly_detection
from app.notifiers.manager import push_important_news, push_news_digest

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _get_interval(key: str, default: int) -> int:
    try:
        async with async_session() as session:
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == key)
            )
            s = result.scalar_one_or_none()
            return int(s.value) if s and s.value else default
    except Exception:
        return default


async def job_fetch_news():
    logger.info("⏰ Running scheduled news fetch")
    try:
        stats = await fetch_all_sources()
        logger.info(f"Fetch stats: {stats}")
        if stats.get("total_saved", 0) > 0:
            await run_importance_scoring()
    except Exception as e:
        logger.error(f"News fetch job error: {e}")


async def job_push_important():
    try:
        await push_important_news()
    except Exception as e:
        logger.error(f"Push important job error: {e}")


async def job_push_digest():
    try:
        await push_news_digest()
    except Exception as e:
        logger.error(f"Push digest job error: {e}")


async def job_anomaly_check():
    try:
        await run_anomaly_detection()
    except Exception as e:
        logger.error(f"Anomaly check job error: {e}")


async def job_morning_report():
    try:
        await generate_daily_report("morning")
    except Exception as e:
        logger.error(f"Morning report job error: {e}")


async def job_evening_report():
    try:
        await generate_daily_report("evening")
    except Exception as e:
        logger.error(f"Evening report job error: {e}")


async def job_cleanup():
    try:
        async with async_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=30)
            await session.execute(
                delete(Article).where(Article.fetched_at < cutoff)
            )
            await session.commit()
            logger.info("Cleaned up old articles")
    except Exception as e:
        logger.error(f"Cleanup job error: {e}")


def start_scheduler():
    scheduler.add_job(job_fetch_news, "interval", minutes=15, id="fetch_news", replace_existing=True)
    scheduler.add_job(job_push_important, "interval", minutes=5, id="push_important", replace_existing=True)
    scheduler.add_job(job_push_digest, "interval", minutes=30, id="push_digest", replace_existing=True)
    scheduler.add_job(job_anomaly_check, "interval", minutes=10, id="anomaly_check", replace_existing=True)
    scheduler.add_job(job_morning_report, "cron", hour=7, minute=30, id="morning_report", replace_existing=True)
    scheduler.add_job(job_evening_report, "cron", hour=22, minute=0, id="evening_report", replace_existing=True)
    scheduler.add_job(job_cleanup, "cron", hour=3, minute=0, id="cleanup", replace_existing=True)
    scheduler.start()
    logger.info("Scheduler started with all jobs")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
