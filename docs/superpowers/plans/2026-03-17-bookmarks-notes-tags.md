# Bookmarks, Notes & Tags Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan.

**Goal:** 让用户可以收藏文章、写批注笔记、打自定义标签，并在专属收藏夹页面管理。

**Architecture:** 新增 `article_bookmarks` 数据库表，挂在现有 `articles` 表上（article_id 外键）。后端新增 `/api/bookmarks/` 路由模块。前端在新闻流每篇文章上加书签按钮，新增独立收藏夹页面。

**Tech Stack:** SQLAlchemy 2.0 async, FastAPI, React + TypeScript, TailwindCSS, lucide-react

---

## Task 1: 数据库模型 `ArticleBookmark`

**Files:**
- Create: `backend/app/models/bookmark.py`
- Modify: `backend/app/main.py` (import model so table is created)

- [ ] 创建 `backend/app/models/bookmark.py`

```python
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base, JSONField

class ArticleBookmark(Base):
    __tablename__ = "article_bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[int] = mapped_column(Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSONField, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("article_id", "user_id", name="uq_bookmark_article_user"),
        Index("ix_bookmark_user_id", "user_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "article_id": self.article_id,
            "user_id": self.user_id,
            "note": self.note,
            "tags": self.tags or [],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
```

- [ ] 在 `backend/app/main.py` 顶部 import 区域加入：
```python
from app.models.bookmark import ArticleBookmark  # noqa: F401 — triggers table creation
```

- [ ] 重启后端确认表已创建（无报错）

---

## Task 2: 后端 API `/api/bookmarks/`

**Files:**
- Create: `backend/app/api/bookmarks.py`
- Modify: `backend/app/api/router.py`

- [ ] 创建 `backend/app/api/bookmarks.py`

```python
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.bookmark import ArticleBookmark
from app.models.article import Article
from app.models.user import User

router = APIRouter()

MAX_TAGS_PER_BOOKMARK = 10
MAX_TAG_LENGTH = 20
MAX_NOTE_LENGTH = 2000


class BookmarkCreate(BaseModel):
    article_id: int
    note: Optional[str] = Field(None, max_length=MAX_NOTE_LENGTH)
    tags: list[str] = Field(default_factory=list)


class BookmarkUpdate(BaseModel):
    note: Optional[str] = Field(None, max_length=MAX_NOTE_LENGTH)
    tags: Optional[list[str]] = None


def _validate_tags(tags: list[str]) -> list[str]:
    if len(tags) > MAX_TAGS_PER_BOOKMARK:
        raise HTTPException(status_code=400, detail=f"标签最多 {MAX_TAGS_PER_BOOKMARK} 个")
    cleaned = []
    for t in tags:
        t = t.strip()
        if not t:
            continue
        if len(t) > MAX_TAG_LENGTH:
            raise HTTPException(status_code=400, detail=f"标签「{t}」超过 {MAX_TAG_LENGTH} 字符")
        cleaned.append(t)
    return list(dict.fromkeys(cleaned))  # deduplicate, preserve order


async def _get_current_user_id(session: AsyncSession, user=None) -> int:
    result = await session.execute(select(User).where(User.username == user.username))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=401, detail="用户不存在")
    return u.id


@router.get("/")
async def list_bookmarks(
    tag: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    user_id = await _get_current_user_id(session, current_user)

    query = (
        select(ArticleBookmark, Article)
        .join(Article, ArticleBookmark.article_id == Article.id)
        .where(ArticleBookmark.user_id == user_id)
        .order_by(desc(ArticleBookmark.created_at))
    )
    count_query = (
        select(func.count(ArticleBookmark.id))
        .where(ArticleBookmark.user_id == user_id)
    )

    if search:
        query = query.where(Article.title.contains(search))
        count_query = count_query.join(Article, ArticleBookmark.article_id == Article.id).where(Article.title.contains(search))

    total = (await session.execute(count_query)).scalar() or 0
    offset = (page - 1) * page_size
    rows = (await session.execute(query.offset(offset).limit(page_size))).all()

    items = []
    for bm, article in rows:
        if tag and tag not in (bm.tags or []):
            continue
        d = bm.to_dict()
        d["article"] = article.to_dict()
        items.append(d)

    return {"items": items, "total": total, "page": page, "pages": (total + page_size - 1) // page_size}


@router.post("/", status_code=201)
async def create_bookmark(
    body: BookmarkCreate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    user_id = await _get_current_user_id(session, current_user)

    # 验证文章存在
    article = (await session.execute(select(Article).where(Article.id == body.article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 已收藏则返回已有记录
    existing = (await session.execute(
        select(ArticleBookmark)
        .where(ArticleBookmark.article_id == body.article_id)
        .where(ArticleBookmark.user_id == user_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="已收藏")

    tags = _validate_tags(body.tags)
    bm = ArticleBookmark(article_id=body.article_id, user_id=user_id, note=body.note, tags=tags)
    session.add(bm)
    await session.commit()
    await session.refresh(bm)
    return bm.to_dict()


@router.put("/{article_id}")
async def update_bookmark(
    article_id: int,
    body: BookmarkUpdate,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    user_id = await _get_current_user_id(session, current_user)
    bm = (await session.execute(
        select(ArticleBookmark)
        .where(ArticleBookmark.article_id == article_id)
        .where(ArticleBookmark.user_id == user_id)
    )).scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="收藏不存在")

    if body.note is not None:
        bm.note = body.note
    if body.tags is not None:
        bm.tags = _validate_tags(body.tags)
    bm.updated_at = datetime.utcnow()
    await session.commit()
    return bm.to_dict()


@router.delete("/{article_id}", status_code=204)
async def delete_bookmark(
    article_id: int,
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    user_id = await _get_current_user_id(session, current_user)
    bm = (await session.execute(
        select(ArticleBookmark)
        .where(ArticleBookmark.article_id == article_id)
        .where(ArticleBookmark.user_id == user_id)
    )).scalar_one_or_none()
    if not bm:
        raise HTTPException(status_code=404, detail="收藏不存在")
    await session.delete(bm)
    await session.commit()


@router.get("/tags")
async def list_tags(
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """返回当前用户所有已用标签（去重排序）"""
    user_id = await _get_current_user_id(session, current_user)
    rows = (await session.execute(
        select(ArticleBookmark.tags).where(ArticleBookmark.user_id == user_id)
    )).scalars().all()
    all_tags: set[str] = set()
    for tags in rows:
        if tags:
            all_tags.update(tags)
    return sorted(all_tags)


@router.get("/status")
async def bookmark_status(
    article_ids: str = Query(..., description="逗号分隔的文章ID"),
    session: AsyncSession = Depends(get_session),
    current_user=Depends(get_current_user),
):
    """批量查询文章是否已收藏，返回 {article_id: bookmark_info | null}"""
    try:
        ids = [int(x) for x in article_ids.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=400, detail="article_ids 格式错误")
    if not ids:
        return {}
    if len(ids) > 100:
        raise HTTPException(status_code=400, detail="最多查询 100 篇")

    user_id = await _get_current_user_id(session, current_user)
    rows = (await session.execute(
        select(ArticleBookmark)
        .where(ArticleBookmark.user_id == user_id)
        .where(ArticleBookmark.article_id.in_(ids))
    )).scalars().all()

    result = {i: None for i in ids}
    for bm in rows:
        result[bm.article_id] = bm.to_dict()
    return result
```

- [ ] 在 `backend/app/api/router.py` 注册路由：
```python
from app.api import bookmarks
api_router.include_router(bookmarks.router, prefix="/bookmarks", tags=["Bookmarks"])
```

- [ ] 验证：curl 测试各接口无 500 错误

---

## Task 3: 前端 API Client

**Files:**
- Modify: `frontend/src/api/index.ts`

- [ ] 在 `index.ts` 新增 `bookmarksApi`：
```typescript
export const bookmarksApi = {
  list: (params: Record<string, unknown> = {}) => client.get('/bookmarks/', { params }),
  create: (article_id: number, note?: string, tags?: string[]) =>
    client.post('/bookmarks/', { article_id, note: note || null, tags: tags || [] }),
  update: (article_id: number, note: string | null, tags: string[]) =>
    client.put(`/bookmarks/${article_id}`, { note, tags }),
  remove: (article_id: number) => client.delete(`/bookmarks/${article_id}`),
  tags: () => client.get('/bookmarks/tags'),
  status: (article_ids: number[]) =>
    client.get('/bookmarks/status', { params: { article_ids: article_ids.join(',') } }),
}
```

---

## Task 4: 新闻流书签按钮

**Files:**
- Modify: `frontend/src/pages/NewsFeed.tsx`

- [ ] 在文章 interface 加 `is_bookmarked?: boolean`
- [ ] 新增 `BookmarkButton` 组件（内联在文件底部）：
  - 点击弹出 Popover（书签面板），包含笔记输入框 + 标签输入
  - 已收藏状态高亮（实心书签图标）
  - 保存/取消收藏按钮
- [ ] 文章列表页加载后批量查询收藏状态（`bookmarksApi.status`）

---

## Task 5: 收藏夹页面

**Files:**
- Create: `frontend/src/pages/Bookmarks.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] 创建 `Bookmarks.tsx`：
  - 顶部：按 tag 筛选（chip 样式）+ 搜索框
  - 文章卡片列表：显示文章标题/来源/时间 + 笔记摘要 + 标签 + 编辑/删除按钮
  - 点击编辑弹出内联编辑区
  - 分页
- [ ] App.tsx 新增路由 `/bookmarks`
- [ ] Layout.tsx 侧边栏新增「收藏夹」入口（Bookmark 图标）

---

## Task 6: 验收 & Commit

- [ ] 测试边界：标签超 10 个报错、笔记超 2000 字符报错、重复收藏返回 409
- [ ] 测试正常流程：收藏 → 写笔记 → 打标签 → 收藏夹筛选 → 取消收藏
- [ ] 测试文章删除后收藏自动消失（级联删除）
- [ ] git commit & push
