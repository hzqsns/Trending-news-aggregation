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
    query = select(Article).order_by(desc(Article.published_at), desc(Article.fetched_at))
    count_query = select(func.count(Article.id))

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
        .where(Article.fetched_at >= since)
        .order_by(desc(Article.importance), desc(Article.published_at))
        .limit(limit)
    )
    result = await session.execute(query)
    return [a.to_dict() for a in result.scalars().all()]


@router.get("/sources")
async def list_sources(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    result = await session.execute(
        select(Article.source, func.count(Article.id).label("count"))
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
