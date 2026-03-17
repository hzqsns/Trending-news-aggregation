from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.article import Article
from app.models.bookmark import ArticleBookmark
from app.models.user import User

router = APIRouter()

MAX_TAGS_PER_BOOKMARK = 10
MAX_TAG_LENGTH = 20
MAX_NOTE_LENGTH = 2000


def _validate_tags(tags: list[str]) -> list[str]:
    cleaned = []
    seen = set()
    for tag in tags:
        tag = tag.strip()
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise HTTPException(status_code=400, detail=f"标签长度不能超过 {MAX_TAG_LENGTH} 个字符")
        if tag not in seen:
            seen.add(tag)
            cleaned.append(tag)
    if len(cleaned) > MAX_TAGS_PER_BOOKMARK:
        raise HTTPException(status_code=400, detail=f"标签数量不能超过 {MAX_TAGS_PER_BOOKMARK} 个")
    return cleaned


class CreateBookmarkBody(BaseModel):
    article_id: int
    note: Optional[str] = None
    tags: list[str] = []


class UpdateBookmarkBody(BaseModel):
    note: Optional[str] = None
    tags: Optional[list[str]] = None


# GET /bookmarks/tags  — must be registered BEFORE /{article_id}
@router.get("/tags")
async def list_tags(
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id
    result = await session.execute(
        select(ArticleBookmark.tags).where(ArticleBookmark.user_id == user_id)
    )
    all_tags: list[str] = []
    for (tags,) in result.all():
        if tags:
            all_tags.extend(tags)
    return sorted(set(all_tags))


# GET /bookmarks/status  — must be registered BEFORE /{article_id}
@router.get("/status")
async def batch_status(
    article_ids: str = Query(..., description="Comma-separated article IDs"),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if not article_ids.strip():
        raise HTTPException(status_code=400, detail="article_ids 不能为空")
    try:
        id_list = [int(x.strip()) for x in article_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="article_ids 格式无效，需为逗号分隔的整数")
    if len(id_list) == 0:
        raise HTTPException(status_code=400, detail="article_ids 不能为空")
    if len(id_list) > 100:
        raise HTTPException(status_code=400, detail="单次最多查询 100 条")

    user_id = current_user.id
    result = await session.execute(
        select(ArticleBookmark).where(
            ArticleBookmark.user_id == user_id,
            ArticleBookmark.article_id.in_(id_list),
        )
    )
    bookmarks = {b.article_id: b.to_dict() for b in result.scalars().all()}
    return {str(aid): bookmarks.get(aid) for aid in id_list}


# GET /bookmarks/
@router.get("/")
async def list_bookmarks(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    query = (
        select(ArticleBookmark, Article)
        .join(Article, ArticleBookmark.article_id == Article.id)
        .where(ArticleBookmark.user_id == user_id)
    )
    if search:
        query = query.where(Article.title.contains(search))

    result = await session.execute(query)
    rows = result.all()

    # Filter by tag in Python (tags stored as JSON list)
    if tag:
        rows = [(bm, art) for bm, art in rows if tag in (bm.tags or [])]

    total = len(rows)
    offset = (page - 1) * page_size
    page_rows = rows[offset: offset + page_size]

    items = []
    for bm, art in page_rows:
        item = bm.to_dict()
        item["article"] = art.to_dict()
        items.append(item)

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": (total + page_size - 1) // page_size,
    }


# POST /bookmarks/
@router.post("/", status_code=201)
async def create_bookmark(
    body: CreateBookmarkBody,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if body.note and len(body.note) > MAX_NOTE_LENGTH:
        raise HTTPException(status_code=400, detail=f"备注长度不能超过 {MAX_NOTE_LENGTH} 个字符")

    user_id = current_user.id

    # Verify article exists
    art_result = await session.execute(select(Article).where(Article.id == body.article_id))
    if not art_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="文章不存在")

    # Check for duplicate
    dup_result = await session.execute(
        select(ArticleBookmark).where(
            ArticleBookmark.user_id == user_id,
            ArticleBookmark.article_id == body.article_id,
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="已收藏该文章")

    tags = _validate_tags(body.tags)
    bookmark = ArticleBookmark(
        article_id=body.article_id,
        user_id=user_id,
        note=body.note,
        tags=tags,
    )
    session.add(bookmark)
    await session.commit()
    await session.refresh(bookmark)
    return bookmark.to_dict()


# PUT /bookmarks/{article_id}
@router.put("/{article_id}")
async def update_bookmark(
    article_id: int,
    body: UpdateBookmarkBody,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    result = await session.execute(
        select(ArticleBookmark).where(
            ArticleBookmark.user_id == user_id,
            ArticleBookmark.article_id == article_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="收藏不存在")

    if body.note is not None:
        if len(body.note) > MAX_NOTE_LENGTH:
            raise HTTPException(status_code=400, detail=f"备注长度不能超过 {MAX_NOTE_LENGTH} 个字符")
        bookmark.note = body.note
    if body.tags is not None:
        bookmark.tags = _validate_tags(body.tags)
    bookmark.updated_at = datetime.utcnow()

    await session.commit()
    await session.refresh(bookmark)
    return bookmark.to_dict()


# DELETE /bookmarks/{article_id}
@router.delete("/{article_id}", status_code=204)
async def delete_bookmark(
    article_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    result = await session.execute(
        select(ArticleBookmark).where(
            ArticleBookmark.user_id == user_id,
            ArticleBookmark.article_id == article_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        raise HTTPException(status_code=404, detail="收藏不存在")

    await session.delete(bookmark)
    await session.commit()
