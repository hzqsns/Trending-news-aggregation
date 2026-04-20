import logging
from datetime import datetime, timedelta

from sqlalchemy import select, delete, desc, func

from app.ai.client import chat_completion
from app.crawlers.steam_market import SteamMarketCrawler
from app.crawlers.cs2_patchnotes import CS2PatchNotesCrawler
from app.database import async_session
from app.models.cs2_item import CS2Item
from app.models.cs2_price import CS2PriceSnapshot
from app.models.cs2_prediction import CS2Prediction
from app.models.cs2_watchlist import CS2Watchlist
from app.models.report import DailyReport
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
    """每日为 Top 热门饰品批量生成 LLM 预测（批量调用，省 90%+ token）"""
    logger.info("⏰ CS2: generating predictions (batch mode)")
    try:
        from app.agents.cs2_market.predictor import predict_batch, PREDICTION_BATCH_SIZE
        async with async_session() as session:
            items = (await session.execute(
                select(CS2Item).where(CS2Item.is_tracked == True).limit(50)  # noqa: E712
            )).scalars().all()

        item_ids = [item.id for item in items]
        total_preds = 0
        for period in ["7d", "14d", "30d"]:
            # 分批，每批 PREDICTION_BATCH_SIZE 个
            for i in range(0, len(item_ids), PREDICTION_BATCH_SIZE):
                batch_ids = item_ids[i:i + PREDICTION_BATCH_SIZE]
                try:
                    preds = await predict_batch(batch_ids, period)
                    total_preds += len(preds)
                except Exception as e:
                    logger.warning(f"Batch predict {period} batch {i} failed: {e}")

        logger.info(f"CS2: generated {total_preds} predictions (batch mode)")
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


async def job_cs2_daily_report():
    """每日生成 CS2 饰品市场日报，写入 daily_reports 表"""
    logger.info("⏰ CS2: generating daily market report")
    try:
        today = datetime.utcnow().date()
        async with async_session() as session:
            existing = (await session.execute(
                select(DailyReport).where(
                    DailyReport.agent_key == AGENT_KEY,
                    DailyReport.report_type == "morning",
                    DailyReport.report_date == today,
                )
            )).scalar_one_or_none()
            if existing:
                logger.info("CS2 daily report already exists, skipping")
                return

            # 收集市场数据
            since = datetime.utcnow() - timedelta(hours=24)

            # 涨幅/跌幅 Top 5
            items = (await session.execute(
                select(CS2Item).where(CS2Item.is_tracked == True).limit(100)  # noqa: E712
            )).scalars().all()

            ranked = []
            for item in items:
                latest = (await session.execute(
                    select(CS2PriceSnapshot)
                    .where(CS2PriceSnapshot.item_id == item.id)
                    .order_by(desc(CS2PriceSnapshot.snapshot_time))
                    .limit(1)
                )).scalar_one_or_none()
                earliest = (await session.execute(
                    select(CS2PriceSnapshot)
                    .where(CS2PriceSnapshot.item_id == item.id, CS2PriceSnapshot.snapshot_time >= since)
                    .order_by(CS2PriceSnapshot.snapshot_time.asc())
                    .limit(1)
                )).scalar_one_or_none()
                if latest and earliest and earliest.price > 0:
                    pct = (latest.price - earliest.price) / earliest.price * 100
                    ranked.append((item.display_name, latest.price, pct, latest.volume))

            if not ranked:
                logger.info("CS2: no price data for daily report")
                return

            ranked.sort(key=lambda x: x[2], reverse=True)
            gainers = ranked[:5]
            losers = ranked[-5:][::-1]

            # 收集最近预测
            predictions = (await session.execute(
                select(CS2Prediction)
                .where(CS2Prediction.period == "7d", CS2Prediction.generated_at >= since)
                .order_by(desc(CS2Prediction.confidence))
                .limit(5)
            )).scalars().all()

            pred_items_map = {}
            if predictions:
                pred_item_ids = [p.item_id for p in predictions]
                pred_items = (await session.execute(
                    select(CS2Item).where(CS2Item.id.in_(pred_item_ids))
                )).scalars().all()
                pred_items_map = {i.id: i for i in pred_items}

        # 构建 LLM prompt
        market_text = f"24h 数据：{len(ranked)} 个饰品追踪中\n\n"
        market_text += "涨幅 Top 5：\n"
        for name, price, pct, vol in gainers:
            market_text += f"- {name}: ¥{price:.0f} ({pct:+.1f}%) 成交量={vol}\n"
        market_text += "\n跌幅 Top 5：\n"
        for name, price, pct, vol in losers:
            market_text += f"- {name}: ¥{price:.0f} ({pct:+.1f}%) 成交量={vol}\n"

        if predictions:
            market_text += "\nAI 高置信预测：\n"
            for p in predictions:
                item_name = pred_items_map.get(p.item_id)
                name = item_name.display_name if item_name else f"Item#{p.item_id}"
                market_text += f"- {name}: {p.direction} ({p.confidence:.0%}) → ¥{p.predicted_price or '?'}\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "你是 CS2 饰品市场分析师。根据以下 24h 市场数据生成简洁的每日行情日报。\n"
                    "用 Markdown 格式，包含：\n"
                    "## 市场概览（1-2段总结）\n"
                    "## 涨幅榜（Top 5 + 简评）\n"
                    "## 跌幅榜（Top 5 + 简评）\n"
                    "## AI 预测信号（如有）\n"
                    "## 操作建议（简短 2-3 条）\n"
                    "中文撰写，专业但简洁，500-800 字。"
                ),
            },
            {"role": "user", "content": market_text},
        ]

        content = await chat_completion(messages, max_tokens=1500, temperature=0.4)
        if not content:
            logger.warning("CS2 daily report: LLM returned empty")
            return

        async with async_session() as session:
            report = DailyReport(
                agent_key=AGENT_KEY,
                report_type="morning",
                report_date=today,
                title=f"{today.isoformat()} CS2 饰品市场日报",
                content=content,
                key_events=[{"gainers": [g[0] for g in gainers], "losers": [l[0] for l in losers]}],
            )
            session.add(report)
            await session.commit()
            logger.info(f"CS2: daily report generated ({len(content)} chars)")

    except Exception as e:
        logger.error(f"CS2 daily report error: {e}")


def register_cs2_jobs(kernel: SchedulerKernel) -> None:
    kernel.add_agent_job(AGENT_KEY, "fetch_prices", job_fetch_prices, "interval", minutes=5)
    kernel.add_agent_job(AGENT_KEY, "fetch_csgoskins", job_fetch_csgoskins, "interval", minutes=30)
    kernel.add_agent_job(AGENT_KEY, "fetch_patchnotes", job_fetch_patchnotes, "cron", hour=8, minute=0)
    kernel.add_agent_job(AGENT_KEY, "generate_predictions", job_generate_predictions, "cron", hour=9, minute=0)
    kernel.add_agent_job(AGENT_KEY, "daily_report", job_cs2_daily_report, "cron", hour=9, minute=30)
    kernel.add_agent_job(AGENT_KEY, "check_alerts", job_check_alerts, "interval", minutes=5)
    kernel.add_agent_job(AGENT_KEY, "cleanup_snapshots", job_cleanup_snapshots, "cron", hour=3, minute=0)


__all__ = [
    "register_cs2_jobs",
    "job_fetch_prices",
    "job_fetch_csgoskins",
    "job_fetch_patchnotes",
    "job_generate_predictions",
    "job_cs2_daily_report",
    "job_check_alerts",
    "job_cleanup_snapshots",
]
