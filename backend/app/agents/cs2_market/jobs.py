import logging
from datetime import datetime, timedelta

from sqlalchemy import select, delete, desc

from app.crawlers.steam_market import SteamMarketCrawler
from app.crawlers.cs2_patchnotes import CS2PatchNotesCrawler
from app.database import async_session
from app.models.cs2_item import CS2Item
from app.models.cs2_price import CS2PriceSnapshot
from app.models.cs2_watchlist import CS2Watchlist
from app.platform.scheduler import SchedulerKernel

logger = logging.getLogger(__name__)

AGENT_KEY = "cs2_market"


async def job_fetch_prices():
    """每 5 分钟拉取热门饰品 Steam Market 价格"""
    logger.info("⏰ CS2: fetching Steam Market prices")
    try:
        async with async_session() as session:
            items = (await session.execute(
                select(CS2Item).where(CS2Item.is_tracked == True).limit(50)  # noqa: E712
            )).scalars().all()

        if not items:
            logger.info("CS2: no tracked items")
            return

        crawler = SteamMarketCrawler()
        names = [item.market_hash_name for item in items]
        results = await crawler.fetch_prices(names, batch_size=20)

        name_to_item = {item.market_hash_name: item for item in items}
        saved = 0
        async with async_session() as session:
            for result in results:
                item = name_to_item.get(result["market_hash_name"])
                if not item or result.get("price") is None:
                    continue
                snapshot = CS2PriceSnapshot(
                    item_id=item.id,
                    platform="steam",
                    price=result["price"],
                    currency="CNY",
                    volume=result.get("volume", 0),
                    listings=0,
                )
                session.add(snapshot)
                saved += 1
            await session.commit()

        logger.info(f"CS2: saved {saved}/{len(results)} price snapshots")
    except Exception as e:
        logger.error(f"CS2 fetch_prices error: {e}")


async def job_fetch_csgoskins():
    """每 30 分钟拉取 CSGOSKINS.GG 多平台比价"""
    logger.info("⏰ CS2: CSGOSKINS crawler placeholder (no API key)")
    # 未配置 API key 时安全跳过，不产生错误


async def job_fetch_patchnotes():
    """每日拉取 CS2 更新日志"""
    logger.info("⏰ CS2: fetching patchnotes")
    try:
        crawler = CS2PatchNotesCrawler()
        items = await crawler.fetch_recent(count=10)
        logger.info(f"CS2: fetched {len(items)} patchnotes")
    except Exception as e:
        logger.error(f"CS2 patchnotes error: {e}")


async def job_generate_predictions():
    """每日为 Top 热门 + 自选饰品生成 LLM 预测"""
    logger.info("⏰ CS2: generating predictions")
    try:
        from app.agents.cs2_market.predictor import predict_item
        async with async_session() as session:
            # Top 50 最活跃的饰品（按最近 24h 快照数）
            items = (await session.execute(
                select(CS2Item).where(CS2Item.is_tracked == True).limit(50)  # noqa: E712
            )).scalars().all()

        count = 0
        for item in items:
            for period in ["7d", "14d", "30d"]:
                try:
                    await predict_item(item.id, period)
                    count += 1
                except Exception as e:
                    logger.warning(f"Predict {item.id} {period} failed: {e}")
        logger.info(f"CS2: generated {count} predictions")
    except Exception as e:
        logger.error(f"CS2 generate_predictions error: {e}")


def check_alert_hit(direction: str | None, current_price: float, target_price: float | None) -> bool:
    """纯函数：判定 watchlist 是否命中目标价。None/缺失条件返回 False。"""
    if target_price is None or direction is None:
        return False
    if direction == "above":
        return current_price >= target_price
    if direction == "below":
        return current_price <= target_price
    return False


async def job_check_alerts():
    """每 5 分钟扫描 watchlist 价格达标触发通知"""
    try:
        async with async_session() as session:
            watches = (await session.execute(
                select(CS2Watchlist).where(
                    CS2Watchlist.target_price.is_not(None),
                    CS2Watchlist.triggered == False,  # noqa: E712
                )
            )).scalars().all()

            triggered_count = 0
            for w in watches:
                latest = (await session.execute(
                    select(CS2PriceSnapshot)
                    .where(CS2PriceSnapshot.item_id == w.item_id)
                    .order_by(desc(CS2PriceSnapshot.snapshot_time))
                    .limit(1)
                )).scalar_one_or_none()
                if not latest:
                    continue

                if check_alert_hit(w.alert_direction, latest.price, w.target_price):
                    w.triggered = True
                    w.triggered_at = datetime.utcnow()
                    triggered_count += 1

            if triggered_count:
                await session.commit()
                logger.info(f"CS2: {triggered_count} alerts triggered")
    except Exception as e:
        logger.error(f"CS2 check_alerts error: {e}")


async def job_cleanup_snapshots():
    """每日清理 90 天前的 snapshots"""
    try:
        cutoff = datetime.utcnow() - timedelta(days=90)
        async with async_session() as session:
            await session.execute(
                delete(CS2PriceSnapshot).where(CS2PriceSnapshot.snapshot_time < cutoff)
            )
            await session.commit()
            logger.info("CS2: cleaned up old snapshots")
    except Exception as e:
        logger.error(f"CS2 cleanup error: {e}")


def register_cs2_jobs(kernel: SchedulerKernel) -> None:
    kernel.add_agent_job(AGENT_KEY, "fetch_prices", job_fetch_prices, "interval", minutes=5)
    kernel.add_agent_job(AGENT_KEY, "fetch_csgoskins", job_fetch_csgoskins, "interval", minutes=30)
    kernel.add_agent_job(AGENT_KEY, "fetch_patchnotes", job_fetch_patchnotes, "cron", hour=8, minute=0)
    kernel.add_agent_job(AGENT_KEY, "generate_predictions", job_generate_predictions, "cron", hour=9, minute=0)
    kernel.add_agent_job(AGENT_KEY, "check_alerts", job_check_alerts, "interval", minutes=5)
    kernel.add_agent_job(AGENT_KEY, "cleanup_snapshots", job_cleanup_snapshots, "cron", hour=3, minute=0)


__all__ = [
    "register_cs2_jobs",
    "job_fetch_prices",
    "job_fetch_csgoskins",
    "job_fetch_patchnotes",
    "job_generate_predictions",
    "job_check_alerts",
    "job_cleanup_snapshots",
]
