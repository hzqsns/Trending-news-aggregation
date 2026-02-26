from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.article import Article
from app.models.alert import Alert
from app.models.sentiment import SentimentSnapshot

router = APIRouter()


@router.get("/overview")
async def get_overview(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_articles = (
        await session.execute(
            select(func.count(Article.id)).where(Article.fetched_at >= today_start)
        )
    ).scalar() or 0

    active_alerts = (
        await session.execute(
            select(func.count(Alert.id)).where(Alert.is_active == True)  # noqa: E712
        )
    ).scalar() or 0

    latest_sentiment = (
        await session.execute(
            select(SentimentSnapshot).order_by(SentimentSnapshot.snapshot_time.desc()).limit(1)
        )
    ).scalar_one_or_none()

    important_today = (
        await session.execute(
            select(func.count(Article.id))
            .where(Article.fetched_at >= today_start)
            .where(Article.importance >= 3)
        )
    ).scalar() or 0

    category_counts = (
        await session.execute(
            select(Article.category, func.count(Article.id))
            .where(Article.fetched_at >= today_start)
            .group_by(Article.category)
        )
    ).all()

    return {
        "today_articles": today_articles,
        "active_alerts": active_alerts,
        "important_today": important_today,
        "sentiment": latest_sentiment.to_dict() if latest_sentiment else {
            "overall_score": 50,
            "label": "neutral",
        },
        "category_breakdown": {row[0]: row[1] for row in category_counts},
    }


@router.get("/sentiment/history")
async def sentiment_history(
    days: int = 7,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(SentimentSnapshot)
        .where(SentimentSnapshot.snapshot_time >= since)
        .order_by(SentimentSnapshot.snapshot_time.asc())
    )
    return [s.to_dict() for s in result.scalars().all()]


@router.get("/stats")
async def get_stats(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    total_articles = (
        await session.execute(select(func.count(Article.id)))
    ).scalar() or 0

    source_stats = (
        await session.execute(
            select(Article.source, func.count(Article.id))
            .group_by(Article.source)
            .order_by(func.count(Article.id).desc())
        )
    ).all()

    hours_data = []
    now = datetime.utcnow()
    for i in range(23, -1, -1):
        start = now - timedelta(hours=i + 1)
        end = now - timedelta(hours=i)
        count = (
            await session.execute(
                select(func.count(Article.id))
                .where(Article.fetched_at >= start)
                .where(Article.fetched_at < end)
            )
        ).scalar() or 0
        hours_data.append({
            "hour": end.strftime("%H:00"),
            "count": count,
        })

    return {
        "total_articles": total_articles,
        "sources": [{"source": s[0], "count": s[1]} for s in source_stats],
        "hourly_volume": hours_data,
    }
