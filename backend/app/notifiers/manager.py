import logging
from datetime import datetime, timedelta

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.article import Article
from app.models.alert import Alert
from app.models.setting import SystemSetting
from app.notifiers.base import Notifier
from app.notifiers.telegram import TelegramNotifier
from app.notifiers.wechat import WeChatNotifier
from app.notifiers.qq import QQNotifier

logger = logging.getLogger(__name__)


async def _get_setting(session: AsyncSession, key: str) -> str:
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == key)
    )
    s = result.scalar_one_or_none()
    return s.value if s else ""


async def _get_enabled_notifiers(session: AsyncSession) -> list[Notifier]:
    notifiers: list[Notifier] = []

    if await _get_setting(session, "telegram_enabled") == "true":
        token = await _get_setting(session, "telegram_bot_token")
        chat_id = await _get_setting(session, "telegram_chat_id")
        if token and chat_id:
            notifiers.append(TelegramNotifier(token, chat_id))

    if await _get_setting(session, "wechat_enabled") == "true":
        token = await _get_setting(session, "pushplus_token")
        if token:
            notifiers.append(WeChatNotifier(token))

    if await _get_setting(session, "qq_enabled") == "true":
        key = await _get_setting(session, "qmsg_key")
        if key:
            notifiers.append(QQNotifier(key))

    return notifiers


async def push_important_news():
    """Push important unpushed articles."""
    async with async_session() as session:
        notifiers = await _get_enabled_notifiers(session)
        if not notifiers:
            return

        result = await session.execute(
            select(Article)
            .where(Article.is_pushed == False)  # noqa: E712
            .where(Article.importance >= 3)
            .order_by(desc(Article.importance))
            .limit(10)
        )
        articles = result.scalars().all()

        for article in articles:
            level_emoji = {5: "🚨", 4: "⚠️", 3: "📢"}.get(article.importance, "📰")
            title = f"{level_emoji} {article.title}"
            content = article.summary or article.title

            for notifier in notifiers:
                try:
                    await notifier.send(title, content, article.url)
                except Exception as e:
                    logger.error(f"Push via {notifier.name} failed: {e}")

            article.is_pushed = True

        if articles:
            await session.commit()
            logger.info(f"Pushed {len(articles)} important articles")


async def push_news_digest():
    """Push a digest of recent news."""
    async with async_session() as session:
        notifiers = await _get_enabled_notifiers(session)
        if not notifiers:
            return

        since = datetime.utcnow() - timedelta(minutes=30)
        result = await session.execute(
            select(Article)
            .where(Article.is_pushed == False)  # noqa: E712
            .where(Article.fetched_at >= since)
            .order_by(desc(Article.importance))
            .limit(20)
        )
        articles = result.scalars().all()
        if not articles:
            return

        lines = [f"📰 *新闻摘要* ({len(articles)} 条)\n"]
        for a in articles:
            emoji = "🔴" if a.importance >= 3 else "🔵"
            lines.append(f"{emoji} {a.title}")
        digest = "\n".join(lines)

        for notifier in notifiers:
            try:
                await notifier.send_markdown("新闻摘要", digest)
            except Exception as e:
                logger.error(f"Digest push via {notifier.name} failed: {e}")

        for a in articles:
            a.is_pushed = True
        await session.commit()
        logger.info(f"Pushed digest with {len(articles)} articles")


async def push_alert(alert: Alert):
    """Push a single alert to all channels."""
    async with async_session() as session:
        notifiers = await _get_enabled_notifiers(session)
        if not notifiers:
            return

        emoji = {"critical": "🚨", "high": "⚠️", "medium": "📢", "low": "ℹ️"}.get(
            alert.level, "📢"
        )
        title = f"{emoji} 预警: {alert.title}"

        for notifier in notifiers:
            try:
                await notifier.send(title, alert.description)
            except Exception as e:
                logger.error(f"Alert push via {notifier.name} failed: {e}")
