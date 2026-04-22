import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.article import Article

router = APIRouter(prefix="/api/tech", tags=["tech"])

AGENT_KEY = "tech_info"


@router.get("/articles")
async def list_tech_articles(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str | None = None,
    search: str | None = None,
    importance_min: int | None = None,
    hours: int | None = None,
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    q = select(Article).where(Article.agent_key == AGENT_KEY)
    count_q = select(func.count(Article.id)).where(Article.agent_key == AGENT_KEY)

    if source:
        q = q.where(Article.source == source)
        count_q = count_q.where(Article.source == source)
    if search:
        like = f"%{search}%"
        q = q.where(Article.title.ilike(like) | Article.summary.ilike(like))
        count_q = count_q.where(Article.title.ilike(like) | Article.summary.ilike(like))
    if importance_min is not None:
        q = q.where(Article.importance >= importance_min)
        count_q = count_q.where(Article.importance >= importance_min)
    if hours:
        cutoff = datetime.now() - timedelta(hours=hours)
        q = q.where(Article.fetched_at >= cutoff)
        count_q = count_q.where(Article.fetched_at >= cutoff)

    total = (await session.execute(count_q)).scalar() or 0
    articles = (
        await session.execute(
            q.order_by(desc(Article.fetched_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()

    return {
        "items": [a.to_dict() for a in articles],
        "total": total,
        "page": page,
        "pages": math.ceil(total / page_size) if total else 0,
    }


@router.get("/dashboard")
async def tech_dashboard(
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    now = datetime.now()
    h24 = now - timedelta(hours=24)

    total = (await session.execute(
        select(func.count(Article.id)).where(Article.agent_key == AGENT_KEY)
    )).scalar() or 0
    today = (await session.execute(
        select(func.count(Article.id)).where(Article.agent_key == AGENT_KEY, Article.fetched_at >= h24)
    )).scalar() or 0
    high_importance = (await session.execute(
        select(func.count(Article.id)).where(
            Article.agent_key == AGENT_KEY, Article.importance >= 3, Article.fetched_at >= h24
        )
    )).scalar() or 0

    # Top sources
    sources = (await session.execute(
        select(Article.source, func.count(Article.id).label("cnt"))
        .where(Article.agent_key == AGENT_KEY, Article.fetched_at >= h24)
        .group_by(Article.source)
        .order_by(desc("cnt"))
        .limit(8)
    )).all()

    return {
        "total_articles": total,
        "articles_24h": today,
        "high_importance_24h": high_importance,
        "top_sources": [{"source": s, "count": c} for s, c in sources],
    }


@router.get("/sources")
async def tech_sources(
    session: AsyncSession = Depends(get_session),
    _user=Depends(get_current_user),
):
    result = await session.execute(
        select(Article.source, func.count(Article.id).label("cnt"))
        .where(Article.agent_key == AGENT_KEY)
        .group_by(Article.source)
        .order_by(desc("cnt"))
    )
    return [{"source": s, "count": c} for s, c in result.all()]
