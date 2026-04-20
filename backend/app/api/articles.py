from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.article import Article

router = APIRouter()


@router.get("/")
async def list_articles(
    category: Optional[str] = None,
    source: Optional[str] = None,
    importance_min: int = 0,
    search: Optional[str] = None,
    hours: int = 24,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    query = select(Article).where(Article.agent_key == "investment").order_by(desc(Article.published_at), desc(Article.fetched_at))
    count_query = select(func.count(Article.id)).where(Article.agent_key == "investment")

    since = datetime.utcnow() - timedelta(hours=hours)
    query = query.where(Article.fetched_at >= since)
    count_query = count_query.where(Article.fetched_at >= since)

    if category:
        query = query.where(Article.category == category)
        count_query = count_query.where(Article.category == category)
    if source:
        query = query.where(Article.source == source)
        count_query = count_query.where(Article.source == source)
    if importance_min > 0:
        query = query.where(Article.importance >= importance_min)
        count_query = count_query.where(Article.importance >= importance_min)
    if search:
        query = query.where(Article.title.contains(search))
        count_query = count_query.where(Article.title.contains(search))

    total = (await session.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    result = await session.execute(query.offset(offset).limit(page_size))
    items = [a.to_dict() for a in result.scalars().all()]

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/trending")
async def trending_articles(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(hours=24)
    query = (
        select(Article)
        .where(Article.agent_key == "investment")
        .where(Article.fetched_at >= since)
        .order_by(desc(Article.importance), desc(Article.published_at))
        .limit(limit)
    )
    result = await session.execute(query)
    return [a.to_dict() for a in result.scalars().all()]


@router.get("/ai-news")
async def ai_industry_news(
    hours: int = Query(24, ge=1, le=720),
    importance_min: int = Query(2, ge=0, le=5),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """AI 行业快讯专项查询（category=ai_industry）。

    - hours: 最近 N 小时（默认 24h，支持到 30 天）
    - importance_min: 最低重要度（默认 2，覆盖 IPO/融资/产品发布）
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    query = (
        select(Article)
        .where(Article.agent_key == "investment")
        .where(Article.category == "ai_industry")
        .where(Article.fetched_at >= since)
        .where(Article.importance >= importance_min)
    )
    if search:
        query = query.where(Article.title.contains(search))
    query = query.order_by(desc(Article.importance), desc(Article.published_at)).limit(limit)

    result = await session.execute(query)
    items = [a.to_dict() for a in result.scalars().all()]

    # 按重要度分桶
    by_importance: dict[int, list] = {}
    for item in items:
        by_importance.setdefault(item["importance"], []).append(item)

    return {
        "total": len(items),
        "hours": hours,
        "items": items,
        "by_importance": {str(k): v for k, v in sorted(by_importance.items(), reverse=True)},
    }


@router.get("/sources")
async def list_sources(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(
        select(Article.source, func.count(Article.id).label("count"))
        .where(Article.agent_key == "investment")
        .group_by(Article.source)
    )
    return [{"source": row[0], "count": row[1]} for row in result.all()]


@router.get("/categories")
async def list_categories(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(
        select(Article.category, func.count(Article.id).label("count"))
        .where(Article.agent_key == "investment")
        .group_by(Article.category)
    )
    return [{"category": row[0], "count": row[1]} for row in result.all()]


@router.get("/{article_id}")
async def get_article(
    article_id: int,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(select(Article).where(Article.id == article_id))
    article = result.scalar_one_or_none()
    if not article:
        return {"error": "Article not found"}
    return article.to_dict()
