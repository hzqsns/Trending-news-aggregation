# 推特博主追踪功能 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 通过自部署的 grok2api 免费获取指定推特博主的投资相关推文，AI 总结后存入新闻系统，并提供独立的前端配置页面管理追踪的博主列表。

**Architecture:** 新增 `TwitterSource` 数据源，通过 grok2api（OpenAI 兼容格式）调用 `grok-3-search` 模型搜索指定博主推文。前端新增独立的「推特追踪」页面（侧边栏入口），用户可增删博主 handle、设置采集频率。博主列表存储在 `system_settings` 表中（JSON 格式），复用现有的 settings 基础设施。

**Tech Stack:** Python httpx (async HTTP), FastAPI router, React + TailwindCSS, 现有 SQLAlchemy 模型

---

## 前置条件

用户需自行部署 grok2api 服务（Docker 一键部署），并在系统设置中配置：
- grok2api 的 Base URL（如 `http://localhost:8001/v1`）
- grok2api 的 API Key（在 grok2api admin 后台获取）

---

### Task 1: 后端 — 新增 Twitter 相关的系统设置项

**Files:**
- Modify: `backend/app/models/setting.py` (DEFAULT_SETTINGS 列表)

**Step 1: 在 DEFAULT_SETTINGS 末尾添加 Twitter 配置项**

在 `backend/app/models/setting.py` 的 `DEFAULT_SETTINGS` 列表末尾、`push_evening_report` 之后追加：

```python
    # --- 推特追踪配置 ---
    {"key": "twitter_enabled", "value": "false", "category": "twitter", "label": "启用推特追踪", "description": "通过 grok2api 追踪推特博主的投资观点", "field_type": "boolean"},
    {"key": "twitter_grok_api_base", "value": "http://localhost:8001/v1", "category": "twitter", "label": "Grok API 地址", "description": "自部署的 grok2api 服务地址", "field_type": "text"},
    {"key": "twitter_grok_api_key", "value": "", "category": "twitter", "label": "Grok API Key", "description": "grok2api 的访问密钥", "field_type": "password"},
    {"key": "twitter_grok_model", "value": "grok-3-search", "category": "twitter", "label": "Grok 模型", "description": "推荐 grok-3-search（带搜索能力）", "field_type": "text"},
    {"key": "twitter_handles", "value": "[]", "category": "twitter", "label": "追踪博主列表", "description": "JSON 数组，如 [\"elonmusk\", \"CathieDWood\"]", "field_type": "json"},
    {"key": "twitter_fetch_interval", "value": "30", "category": "twitter", "label": "采集间隔（分钟）", "description": "推特数据采集的时间间隔，建议 >= 30 以节省配额", "field_type": "number"},
```

**Step 2: 验证**

Run: `cd /Users/heziqi/Project/Trending-news-aggregation/backend && source venv/bin/activate && python -c "from app.models.setting import DEFAULT_SETTINGS; print(len([s for s in DEFAULT_SETTINGS if s['category']=='twitter']))"`
Expected: `6`

**Step 3: Commit**

```bash
git add backend/app/models/setting.py
git commit -m "feat: add twitter tracking settings to DEFAULT_SETTINGS"
```

---

### Task 2: 后端 — 设置 API 添加 twitter 分类

**Files:**
- Modify: `backend/app/api/settings.py` (categories 端点)

**Step 1: 在 setting_categories 返回值中添加 twitter 分类**

在 `backend/app/api/settings.py` 的 `setting_categories` 函数中，`push_strategy` 之后添加：

```python
            {"key": "twitter", "label": "推特追踪"},
```

完整的 categories 列表变为：
```python
    return {
        "categories": [
            {"key": "system", "label": "系统配置"},
            {"key": "ai", "label": "AI 配置"},
            {"key": "sources", "label": "数据源配置"},
            {"key": "notifications", "label": "推送渠道"},
            {"key": "push_strategy", "label": "推送策略"},
            {"key": "twitter", "label": "推特追踪"},
        ]
    }
```

**Step 2: Commit**

```bash
git add backend/app/api/settings.py
git commit -m "feat: add twitter category to settings API"
```

---

### Task 3: 后端 — 新增 Twitter 博主管理 API

**Files:**
- Create: `backend/app/api/twitter.py`
- Modify: `backend/app/api/router.py`

**Step 1: 创建 twitter API 路由**

创建 `backend/app/api/twitter.py`：

```python
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_session
from app.models.setting import SystemSetting

router = APIRouter()
logger = logging.getLogger(__name__)


class HandleAdd(BaseModel):
    handle: str


class HandleRemove(BaseModel):
    handle: str


async def _get_handles(session: AsyncSession) -> list[str]:
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "twitter_handles")
    )
    setting = result.scalar_one_or_none()
    if not setting or not setting.value:
        return []
    try:
        return json.loads(setting.value)
    except json.JSONDecodeError:
        return []


async def _save_handles(session: AsyncSession, handles: list[str]):
    result = await session.execute(
        select(SystemSetting).where(SystemSetting.key == "twitter_handles")
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = json.dumps(handles)
        await session.commit()


@router.get("/handles")
async def list_handles(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    handles = await _get_handles(session)
    return {"handles": handles}


@router.post("/handles")
async def add_handle(
    body: HandleAdd,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    handle = body.handle.strip().lstrip("@")
    if not handle:
        raise HTTPException(status_code=400, detail="Handle cannot be empty")

    handles = await _get_handles(session)
    if handle in handles:
        raise HTTPException(status_code=400, detail="Handle already exists")

    handles.append(handle)
    await _save_handles(session, handles)
    return {"handles": handles}


@router.delete("/handles/{handle}")
async def remove_handle(
    handle: str,
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    handles = await _get_handles(session)
    handle = handle.strip().lstrip("@")
    if handle not in handles:
        raise HTTPException(status_code=404, detail="Handle not found")

    handles.remove(handle)
    await _save_handles(session, handles)
    return {"handles": handles}


@router.post("/fetch")
async def manual_fetch(
    session: AsyncSession = Depends(get_session),
    _=Depends(get_current_user),
):
    """手动触发一次推特采集"""
    from app.sources.twitter import TwitterSource
    source = TwitterSource()
    try:
        items = await source.fetch()
        if items:
            from app.sources.manager import _save_items
            saved, new_articles = await _save_items(session, items)
            return {"fetched": len(items), "saved": saved}
        return {"fetched": 0, "saved": 0}
    except Exception as e:
        logger.error(f"Manual twitter fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 2: 注册路由到 router.py**

在 `backend/app/api/router.py` 中添加导入和注册：

```python
from app.api import auth_routes, articles, dashboard, settings, reports, alerts, skills, ws, twitter

# 在现有 include_router 列表末尾添加:
api_router.include_router(twitter.router, prefix="/twitter", tags=["Twitter"])
```

**Step 3: 验证**

Run: `cd /Users/heziqi/Project/Trending-news-aggregation/backend && source venv/bin/activate && python -c "from app.api.router import api_router; print([r.path for r in api_router.routes if 'twitter' in str(r.path)])"`
Expected: 包含 `/api/twitter` 相关路径

**Step 4: Commit**

```bash
git add backend/app/api/twitter.py backend/app/api/router.py
git commit -m "feat: add twitter handles management API"
```

---

### Task 4: 后端 — 新增 TwitterSource 数据源

**Files:**
- Create: `backend/app/sources/twitter.py`

**Step 1: 创建 TwitterSource**

创建 `backend/app/sources/twitter.py`：

```python
import json
import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select

from app.database import async_session
from app.models.setting import SystemSetting
from app.sources.base import NewsSource, NewsItem

logger = logging.getLogger(__name__)

# 每次最多查询的博主数量（grok2api 配额有限，分批处理）
BATCH_SIZE = 5


async def _get_twitter_config() -> dict:
    async with async_session() as session:
        keys = [
            "twitter_enabled", "twitter_grok_api_base", "twitter_grok_api_key",
            "twitter_grok_model", "twitter_handles",
        ]
        result = await session.execute(
            select(SystemSetting).where(SystemSetting.key.in_(keys))
        )
        settings = {s.key: s.value for s in result.scalars().all()}

    handles = []
    try:
        handles = json.loads(settings.get("twitter_handles", "[]"))
    except json.JSONDecodeError:
        pass

    return {
        "enabled": settings.get("twitter_enabled", "false") == "true",
        "api_base": settings.get("twitter_grok_api_base", "http://localhost:8001/v1"),
        "api_key": settings.get("twitter_grok_api_key", ""),
        "model": settings.get("twitter_grok_model", "grok-3-search"),
        "handles": handles,
    }


async def _query_grok_for_handles(config: dict, handles: list[str]) -> list[NewsItem]:
    """调用 grok2api 搜索一批博主的最新投资推文"""
    items = []
    handles_str = ", ".join(f"@{h}" for h in handles)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

    prompt = f"""请搜索以下推特博主从 {yesterday} 到 {today} 的最新推文，重点关注投资、金融、市场、加密货币相关内容：

博主列表：{handles_str}

请为每位博主总结他们最近的重要观点，格式要求：
1. 每条观点单独一段
2. 每段开头标注博主 @handle
3. 包含具体的投资观点、市场判断、推荐标的等关键信息
4. 忽略日常闲聊、转发广告等无关内容
5. 如果某位博主近期无投资相关推文，简要说明即可

请用中文回复。"""

    url = f"{config['api_base'].rstrip('/')}/chat/completions"
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "system", "content": "你是一个专业的投资信息分析助手，擅长从社交媒体中提取有价值的投资观点。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2000,
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {config['api_key']}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code != 200:
                logger.error(f"Grok API error {resp.status_code}: {resp.text[:300]}")
                return items

            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # 将整个总结作为一条新闻存入
            items.append(NewsItem(
                title=f"推特投资观点汇总 ({today}) — {handles_str}",
                url=f"https://x.com/search?q={'%20OR%20'.join(f'from:{h}' for h in handles)}&f=live",
                source="Twitter/Grok",
                category="twitter",
                summary=content[:500] if len(content) > 500 else content,
                content=content,
                published_at=datetime.utcnow(),
                importance=2,
            ))

    except Exception as e:
        logger.error(f"Error querying Grok for twitter handles {handles}: {e}")

    return items


class TwitterSource(NewsSource):
    name = "Twitter"
    category = "twitter"
    enabled_key = "twitter_enabled"

    async def fetch(self) -> list[NewsItem]:
        config = await _get_twitter_config()

        if not config["enabled"]:
            return []
        if not config["api_key"]:
            logger.warning("Twitter tracking enabled but Grok API key not set")
            return []
        if not config["handles"]:
            logger.info("Twitter tracking enabled but no handles configured")
            return []

        all_items = []

        # 分批处理博主（每批最多 BATCH_SIZE 个）
        for i in range(0, len(config["handles"]), BATCH_SIZE):
            batch = config["handles"][i:i + BATCH_SIZE]
            items = await _query_grok_for_handles(config, batch)
            all_items.extend(items)

        logger.info(f"Twitter source fetched {len(all_items)} items for {len(config['handles'])} handles")
        return all_items
```

**Step 2: 验证语法**

Run: `cd /Users/heziqi/Project/Trending-news-aggregation/backend && source venv/bin/activate && python -c "from app.sources.twitter import TwitterSource; print(TwitterSource.name, TwitterSource.enabled_key)"`
Expected: `Twitter twitter_enabled`

**Step 3: Commit**

```bash
git add backend/app/sources/twitter.py
git commit -m "feat: add TwitterSource using grok2api for tweet tracking"
```

---

### Task 5: 后端 — 注册 TwitterSource 到数据源管理器

**Files:**
- Modify: `backend/app/sources/manager.py`

**Step 1: 添加导入和注册**

在 `manager.py` 顶部添加导入：
```python
from app.sources.twitter import TwitterSource
```

在 `ALL_SOURCES` 列表中添加：
```python
ALL_SOURCES: list[NewsSource] = [
    RSSSource(),
    CryptoSource(),
    NewsAPISource(),
    TwitterSource(),
]
```

**Step 2: Commit**

```bash
git add backend/app/sources/manager.py
git commit -m "feat: register TwitterSource in source manager"
```

---

### Task 6: 后端 — 添加推特独立的定时采集任务

**Files:**
- Modify: `backend/app/scheduler.py`

**Step 1: 添加推特采集任务**

在 `scheduler.py` 中添加导入和任务函数：

在文件顶部导入区添加：
```python
from app.sources.twitter import TwitterSource
```

在 `job_cleanup` 函数之后添加新函数：
```python
async def job_fetch_twitter():
    logger.info("⏰ Running scheduled twitter fetch")
    try:
        source = TwitterSource()
        items = await source.fetch()
        if items:
            async with async_session() as session:
                from app.sources.manager import _save_items
                saved, new_articles = await _save_items(session, items)
                logger.info(f"Twitter fetch: {len(items)} fetched, {saved} saved")
                if new_articles:
                    try:
                        from app.api.ws import broadcast_new_articles
                        await broadcast_new_articles(new_articles)
                    except Exception as e:
                        logger.debug(f"WebSocket broadcast skipped: {e}")
                if saved > 0:
                    await run_importance_scoring()
    except Exception as e:
        logger.error(f"Twitter fetch job error: {e}")
```

在 `start_scheduler` 函数中添加（在 `scheduler.start()` 之前）：
```python
    scheduler.add_job(job_fetch_twitter, "interval", minutes=30, id="fetch_twitter", replace_existing=True)
```

**Step 2: Commit**

```bash
git add backend/app/scheduler.py
git commit -m "feat: add scheduled twitter fetch job (30min interval)"
```

---

### Task 7: 前端 — 添加推特追踪 API 客户端

**Files:**
- Modify: `frontend/src/api/index.ts`

**Step 1: 添加 twitterApi**

在 `frontend/src/api/index.ts` 的 `settingsApi` 之后添加：

```typescript
export const twitterApi = {
  listHandles: () => client.get('/twitter/handles'),
  addHandle: (handle: string) => client.post('/twitter/handles', { handle }),
  removeHandle: (handle: string) => client.delete(`/twitter/handles/${handle}`),
  manualFetch: () => client.post('/twitter/fetch'),
}
```

**Step 2: Commit**

```bash
git add frontend/src/api/index.ts
git commit -m "feat: add twitter API client"
```

---

### Task 8: 前端 — 创建推特追踪配置页面

**Files:**
- Create: `frontend/src/pages/TwitterTracking.tsx`

**Step 1: 创建页面组件**

创建 `frontend/src/pages/TwitterTracking.tsx`：

```tsx
import { useEffect, useState } from 'react'
import { Plus, Trash2, RefreshCw, Twitter, ExternalLink } from 'lucide-react'
import { twitterApi, settingsApi } from '@/api'

export default function TwitterTracking() {
  const [handles, setHandles] = useState<string[]>([])
  const [newHandle, setNewHandle] = useState('')
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [fetchResult, setFetchResult] = useState<string | null>(null)
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [savingSettings, setSavingSettings] = useState(false)

  const loadHandles = async () => {
    try {
      const resp = await twitterApi.listHandles()
      setHandles(resp.data.handles)
    } catch (e) {
      console.error(e)
    }
  }

  const loadSettings = async () => {
    try {
      const resp = await settingsApi.list('twitter')
      const items = resp.data.twitter || []
      const s: Record<string, string> = {}
      for (const item of items) {
        if (item.key !== 'twitter_handles') {
          s[item.key] = item.value ?? ''
        }
      }
      setSettings(s)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    Promise.all([loadHandles(), loadSettings()]).finally(() => setLoading(false))
  }, [])

  const addHandle = async () => {
    const h = newHandle.trim().replace(/^@/, '')
    if (!h) return
    setAdding(true)
    try {
      const resp = await twitterApi.addHandle(h)
      setHandles(resp.data.handles)
      setNewHandle('')
    } catch (e: any) {
      alert(e.response?.data?.detail || '添加失败')
    } finally {
      setAdding(false)
    }
  }

  const removeHandle = async (handle: string) => {
    try {
      const resp = await twitterApi.removeHandle(handle)
      setHandles(resp.data.handles)
    } catch (e) {
      console.error(e)
    }
  }

  const manualFetch = async () => {
    setFetching(true)
    setFetchResult(null)
    try {
      const resp = await twitterApi.manualFetch()
      setFetchResult(`采集完成：获取 ${resp.data.fetched} 条，新增 ${resp.data.saved} 条`)
    } catch (e: any) {
      setFetchResult(`采集失败：${e.response?.data?.detail || e.message}`)
    } finally {
      setFetching(false)
    }
  }

  const saveSettings = async () => {
    setSavingSettings(true)
    try {
      await settingsApi.batchUpdate(settings)
      setSavingSettings(false)
    } catch (e) {
      console.error(e)
      setSavingSettings(false)
    }
  }

  if (loading) {
    return <div className="p-8 text-center text-text-secondary">加载中...</div>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">推特博主追踪</h2>
        <button
          onClick={manualFetch}
          disabled={fetching || handles.length === 0}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          <RefreshCw size={16} className={fetching ? 'animate-spin' : ''} />
          {fetching ? '采集中...' : '立即采集'}
        </button>
      </div>

      {fetchResult && (
        <div className="mb-4 p-3 bg-card border border-border rounded-lg text-sm">
          {fetchResult}
        </div>
      )}

      {/* 博主列表 */}
      <div className="bg-card rounded-xl border border-border mb-6">
        <div className="p-5 border-b border-border">
          <h3 className="font-semibold">追踪的博主</h3>
          <p className="text-xs text-text-secondary mt-1">添加推特博主的用户名（不含 @），系统会定时采集他们的投资相关推文</p>
        </div>

        {/* 添加输入框 */}
        <div className="p-4 border-b border-border">
          <div className="flex gap-2">
            <div className="relative flex-1 max-w-md">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary text-sm">@</span>
              <input
                type="text"
                value={newHandle}
                onChange={(e) => setNewHandle(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addHandle()}
                placeholder="输入推特用户名，如 elonmusk"
                className="w-full pl-8 pr-3 py-2 rounded-lg border border-border text-sm"
              />
            </div>
            <button
              onClick={addHandle}
              disabled={adding || !newHandle.trim()}
              className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
            >
              <Plus size={16} />
              添加
            </button>
          </div>
        </div>

        {/* 博主列表 */}
        <div className="divide-y divide-border">
          {handles.map((handle) => (
            <div key={handle} className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center">
                  <Twitter size={16} className="text-blue-500" />
                </div>
                <div>
                  <span className="text-sm font-medium">@{handle}</span>
                  <a
                    href={`https://x.com/${handle}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-2 text-text-secondary hover:text-primary"
                  >
                    <ExternalLink size={12} className="inline" />
                  </a>
                </div>
              </div>
              <button
                onClick={() => removeHandle(handle)}
                className="p-1.5 text-text-secondary hover:text-red-500 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              >
                <Trash2 size={16} />
              </button>
            </div>
          ))}
          {handles.length === 0 && (
            <div className="p-8 text-center text-text-secondary text-sm">
              暂未添加任何博主，请在上方输入框添加
            </div>
          )}
        </div>
      </div>

      {/* Grok API 配置 */}
      <div className="bg-card rounded-xl border border-border">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h3 className="font-semibold">Grok API 配置</h3>
            <p className="text-xs text-text-secondary mt-1">配置自部署的 grok2api 服务连接信息</p>
          </div>
          <button
            onClick={saveSettings}
            disabled={savingSettings}
            className="px-3 py-1.5 bg-primary hover:bg-primary-dark text-white rounded-lg text-xs transition-colors disabled:opacity-50"
          >
            {savingSettings ? '保存中...' : '保存配置'}
          </button>
        </div>
        <div className="divide-y divide-border">
          <SettingRow
            label="启用推特追踪"
            description="开启后系统会定时采集配置的博主推文"
            value={settings.twitter_enabled ?? 'false'}
            type="boolean"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_enabled: v }))}
          />
          <SettingRow
            label="Grok API 地址"
            description="自部署的 grok2api 服务地址"
            value={settings.twitter_grok_api_base ?? ''}
            type="text"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_grok_api_base: v }))}
          />
          <SettingRow
            label="Grok API Key"
            description="grok2api 的访问密钥"
            value={settings.twitter_grok_api_key ?? ''}
            type="password"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_grok_api_key: v }))}
          />
          <SettingRow
            label="Grok 模型"
            description="推荐 grok-3-search（带搜索能力）"
            value={settings.twitter_grok_model ?? 'grok-3-search'}
            type="text"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_grok_model: v }))}
          />
          <SettingRow
            label="采集间隔（分钟）"
            description="建议 >= 30 以节省配额"
            value={settings.twitter_fetch_interval ?? '30'}
            type="number"
            onChange={(v) => setSettings((s) => ({ ...s, twitter_fetch_interval: v }))}
          />
        </div>
      </div>
    </div>
  )
}

function SettingRow({
  label,
  description,
  value,
  type,
  onChange,
}: {
  label: string
  description: string
  value: string
  type: 'text' | 'password' | 'number' | 'boolean'
  onChange: (v: string) => void
}) {
  const [showPwd, setShowPwd] = useState(false)

  return (
    <div className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="sm:w-1/3">
        <div className="text-sm font-medium">{label}</div>
        <div className="text-xs text-text-secondary">{description}</div>
      </div>
      <div className="sm:w-2/3">
        {type === 'boolean' ? (
          <button
            type="button"
            onClick={() => onChange(value === 'true' ? 'false' : 'true')}
            className={`relative w-12 h-6 rounded-full transition-colors ${value === 'true' ? 'bg-green-500' : 'bg-gray-300'}`}
          >
            <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${value === 'true' ? 'left-6' : 'left-0.5'}`} />
          </button>
        ) : type === 'password' ? (
          <div className="relative max-w-md">
            <input
              type={showPwd ? 'text' : 'password'}
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-full px-3 py-2 pr-10 rounded-lg border border-border text-sm"
            />
            <button
              type="button"
              onClick={() => setShowPwd(!showPwd)}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary"
            >
              {showPwd ? '🙈' : '👁️'}
            </button>
          </div>
        ) : (
          <input
            type={type}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="w-full max-w-md px-3 py-2 rounded-lg border border-border text-sm"
          />
        )}
      </div>
    </div>
  )
}
```

**Step 2: Commit**

```bash
git add frontend/src/pages/TwitterTracking.tsx
git commit -m "feat: add TwitterTracking page component"
```

---

### Task 9: 前端 — 注册路由和侧边栏入口

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

**Step 1: App.tsx 添加路由**

在 `frontend/src/App.tsx` 中：

添加导入（与其他 page 导入放一起）：
```tsx
import TwitterTracking from '@/pages/TwitterTracking'
```

在 `<Route path="/settings" element={<Settings />} />` 之后添加：
```tsx
          <Route path="/twitter" element={<TwitterTracking />} />
```

**Step 2: Layout.tsx 添加侧边栏**

在 `frontend/src/components/Layout.tsx` 中：

在 import 中添加 `Twitter` icon（lucide-react 中实际名称可能为 `Twitter` 或需要其他图标）：

将 import 行修改为：
```tsx
import {
  LayoutDashboard, Newspaper, FileText, AlertTriangle, Cpu,
  Settings, LogOut, Moon, Sun, Monitor, Menu, X, AtSign,
} from 'lucide-react'
```

在 `navItems` 数组中，`Settings` 之前添加：
```tsx
  { to: '/twitter', icon: AtSign, label: '推特追踪' },
```

完整的 navItems：
```tsx
const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/news', icon: Newspaper, label: '新闻流' },
  { to: '/reports', icon: FileText, label: 'AI 日报' },
  { to: '/alerts', icon: AlertTriangle, label: '预警中心' },
  { to: '/skills', icon: Cpu, label: 'Skills' },
  { to: '/twitter', icon: AtSign, label: '推特追踪' },
  { to: '/settings', icon: Settings, label: '系统设置' },
]
```

**Step 3: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add twitter tracking route and sidebar nav item"
```

---

### Task 10: 前端设置页面 — 添加 twitter 分类显示

**Files:**
- Modify: `frontend/src/pages/Settings.tsx`

**Step 1: 在 categoryInfo 中添加 twitter**

在 `frontend/src/pages/Settings.tsx` 的 `categoryInfo` 对象中添加：

```typescript
  twitter: { label: '推特追踪', icon: '🐦' },
```

**Step 2: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: add twitter category to settings page"
```

---

### Task 11: 初始化设置数据 — main.py 添加 env 映射

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/config.py`

**Step 1: config.py 添加环境变量**

在 `backend/app/config.py` 的 Settings 类中添加（与其他可选环境变量放一起）：

```python
    TWITTER_GROK_API_BASE: str = ""
    TWITTER_GROK_API_KEY: str = ""
```

**Step 2: main.py 添加 env 映射**

在 `backend/app/main.py` 的 `_init_settings` 函数中，`env_mapping` 字典末尾添加：

```python
            "twitter_grok_api_base": settings.TWITTER_GROK_API_BASE,
            "twitter_grok_api_key": settings.TWITTER_GROK_API_KEY,
```

**Step 3: Commit**

```bash
git add backend/app/config.py backend/app/main.py
git commit -m "feat: add twitter env vars to config and init mapping"
```

---

### Task 12: 集成测试 — 启动验证

**Step 1: 删除旧数据库（重新初始化以加载新 DEFAULT_SETTINGS）**

```bash
cd /Users/heziqi/Project/Trending-news-aggregation/backend
mv data/news_agent.db data/news_agent.db.bak 2>/dev/null || true
```

**Step 2: 启动后端验证**

```bash
cd /Users/heziqi/Project/Trending-news-aggregation
./start.sh
```

Expected: 后端启动无报错，日志显示 settings 初始化成功

**Step 3: 验证 API 端点**

```bash
# 登录获取 token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 验证 twitter handles API
curl -s -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/api/twitter/handles
# Expected: {"handles":[]}

# 添加一个 handle
curl -s -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"handle":"elonmusk"}' \
  http://127.0.0.1:8000/api/twitter/handles
# Expected: {"handles":["elonmusk"]}

# 验证 twitter 设置存在
curl -s -H "Authorization: Bearer $TOKEN" "http://127.0.0.1:8000/api/settings/?category=twitter"
# Expected: 包含 twitter_enabled 等配置项
```

**Step 4: 验证前端页面**

浏览器访问 `http://localhost:5173/twitter`
Expected: 看到推特博主追踪页面，可以添加/删除博主，Grok API 配置区域正常显示

**Step 5: 恢复旧数据库（如果需要保留原有数据）**

```bash
cd /Users/heziqi/Project/Trending-news-aggregation/backend
mv data/news_agent.db.bak data/news_agent.db 2>/dev/null || true
```

注意：恢复后需要手动插入新的 settings，或在 `_init_settings` 启动时会自动补充缺失的 key。

---

## 文件变更总览

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/setting.py` | 修改 | 添加 6 个 twitter 配置项到 DEFAULT_SETTINGS |
| `backend/app/api/settings.py` | 修改 | categories 添加 twitter |
| `backend/app/api/twitter.py` | 新建 | 博主管理 + 手动采集 API |
| `backend/app/api/router.py` | 修改 | 注册 twitter 路由 |
| `backend/app/sources/twitter.py` | 新建 | TwitterSource 数据源（调用 grok2api） |
| `backend/app/sources/manager.py` | 修改 | 注册 TwitterSource |
| `backend/app/scheduler.py` | 修改 | 添加 twitter 定时采集任务 |
| `backend/app/config.py` | 修改 | 添加 TWITTER 环境变量 |
| `backend/app/main.py` | 修改 | env 映射添加 twitter |
| `frontend/src/api/index.ts` | 修改 | 添加 twitterApi |
| `frontend/src/pages/TwitterTracking.tsx` | 新建 | 推特追踪配置页面 |
| `frontend/src/pages/Settings.tsx` | 修改 | categoryInfo 添加 twitter |
| `frontend/src/components/Layout.tsx` | 修改 | 侧边栏添加推特追踪入口 |
| `frontend/src/App.tsx` | 修改 | 添加 /twitter 路由 |
