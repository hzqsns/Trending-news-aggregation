# 实施计划：金融日历 + Twitter 观点日报

> 日期：2026-03-23
> 任务类型：全栈（后端 + 前端）
> 依赖：无外部付费 API

---

## 技术方案

### 功能 A：Twitter 观点日报（优先实现，复用现有基础设施）

**思路**：tweets 已存为 `category="twitter"` 的 articles。新增 `generate_twitter_digest()` 函数，查询近 24h Twitter 文章，按 handle 分组后调用 LLM 生成结构化观点摘要，以 `report_type="twitter_digest"` 存入现有 `daily_reports` 表（零 schema 变更）。前端在 `TwitterTracking.tsx` 加"观点日报"标签页。

### 功能 B：金融日历（新表 + 新页面）

**思路**：新建 `CalendarEvent` 表存储三类事件：
- `economic`：宏观经济数据（CPI、FOMC、NFP 等）—— 通过免费 API 抓取 + 手动预置
- `earnings`：美股财报日期 —— 通过 Alpha Vantage 免费 API 或 Yahoo Finance 抓取
- `custom`：用户自定义事件

前端新增 `Calendar.tsx` 页面，列表视图（比日历网格更稳定），按类型 badge 区分，显示距今倒计时。

---

## 实施步骤

### 阶段一：Twitter 观点日报（后端）

#### Task A1：`skills/engine.py` 新增 `generate_twitter_digest()`

**文件**：`backend/app/skills/engine.py`

```python
async def generate_twitter_digest() -> bool:
    """生成 Twitter 博主观点日报，存入 daily_reports 表。"""
    # 1. 查近 24h Twitter 文章
    cutoff = datetime.utcnow() - timedelta(hours=24)
    async with async_session() as session:
        result = await session.execute(
            select(Article)
            .where(Article.category == "twitter")
            .where(Article.published_at >= cutoff)
            .order_by(Article.published_at.desc())
        )
        articles = result.scalars().all()

    if not articles:
        logger.info("Twitter digest: no tweets in last 24h, skipping")
        return False

    # 2. 按 handle 分组（从 title 解析 "@handle:" 前缀）
    handle_map: dict[str, list[str]] = {}
    for a in articles:
        handle = a.source_handle or _extract_handle(a.title)
        handle_map.setdefault(handle, []).append(a.content or a.title)

    # 3. 构建 prompt
    handles_text = ""
    for handle, tweets in handle_map.items():
        handles_text += f"\n### @{handle}\n" + "\n".join(f"- {t[:200]}" for t in tweets[:10])

    messages = [
        {"role": "system", "content": (
            "你是投研助手。请根据以下推特博主的推文，生成结构化的观点日报。\n"
            "格式：每位博主一节（二级标题），列出核心观点（3-5条）；最后加「综合主题」节，总结共同信号。\n"
            "语言：中文。输出 Markdown 格式。"
        )},
        {"role": "user", "content": f"今日追踪博主推文：\n{handles_text}"},
    ]
    content = await chat_completion(messages, max_tokens=2000, temperature=0.4)
    if not content:
        return False

    # 4. 存入 daily_reports
    today = datetime.utcnow().date()
    async with async_session() as session:
        existing = (await session.execute(
            select(DailyReport)
            .where(DailyReport.report_type == "twitter_digest")
            .where(DailyReport.report_date == today)
        )).scalar_one_or_none()

        if existing:
            existing.content = content
            existing.title = f"{today} 推特博主观点日报"
        else:
            report = DailyReport(
                report_type="twitter_digest",
                report_date=today,
                title=f"{today} 推特博主观点日报",
                content=content,
                key_events=[],
            )
            session.add(report)
        await session.commit()
    return True


def _extract_handle(title: str) -> str:
    """从 '@handle: ...' 格式的标题中提取 handle。"""
    if title.startswith("@") and ":" in title:
        return title.split(":")[0][1:]
    return "unknown"
```

#### Task A2：`scheduler.py` 新增定时任务

**文件**：`backend/app/scheduler.py`

```python
# 每天 09:00 生成 Twitter 观点日报
scheduler.add_job(job_twitter_digest, CronTrigger(hour=9, minute=0), id="job_twitter_digest", ...)

async def job_twitter_digest():
    from app.skills.engine import generate_twitter_digest
    await generate_twitter_digest()
```

#### Task A3：`api/reports.py` 扩展 report_type 过滤

**文件**：`backend/app/api/reports.py`

在现有 `GET /` 端点的 query 中加 `report_type: Optional[str] = None` 参数，并在 filter 中使用。

---

### 阶段二：Twitter 观点日报（前端）

#### Task A4：`TwitterTracking.tsx` 新增"观点日报"标签页

**文件**：`frontend/src/pages/TwitterTracking.tsx`

- 顶部加两个 tab：`博主管理` / `观点日报`
- 观点日报 tab：调用 `GET /api/reports/?report_type=twitter_digest&limit=7`，展示最近 7 天报告列表
- 点击报告展开 Markdown 渲染（复用 `react-markdown + remark-gfm`，与 Reports 页一致）
- 顶部加"立即生成"按钮，调用新增的 `POST /api/reports/generate-twitter-digest` 端点

#### Task A5：`api/index.ts` 扩展 reportsApi

```typescript
export const reportsApi = {
  // ...existing...
  listByType: (report_type: string, limit = 7) =>
    client.get('/reports/', { params: { report_type, limit } }),
  generateTwitterDigest: () =>
    client.post('/reports/generate-twitter-digest'),
}
```

---

### 阶段三：金融日历（后端）

#### Task B1：新建 `models/calendar_event.py`

**文件**：`backend/app/models/calendar_event.py`

```python
class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # economic / earnings / custom
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_time: Mapped[str | None] = mapped_column(String(10), nullable=True)   # "08:30" UTC
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    importance: Mapped[str] = mapped_column(String(10), default="medium")  # high/medium/low
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)   # "FRED" / "manual" / etc.
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONField, nullable=True)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_calendar_event_date", "event_date"),
        Index("ix_calendar_event_type", "event_type"),
    )
```

#### Task B2：`api/calendar.py` 新建路由

**文件**：`backend/app/api/calendar.py`

端点：
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/` | 列表，支持 `start`/`end` 日期范围、`event_type` 过滤 |
| POST | `/` | 创建自定义事件 |
| PUT | `/{id}` | 更新事件 |
| DELETE | `/{id}` | 删除（仅 custom 类型） |
| POST | `/fetch` | 触发从外部源抓取最新事件 |

**数据源策略（免费）**：

- **经济事件**：预置 2026 年 FOMC 会议日期（美联储官网公开）+ CPI/NFP/PCE 发布日（BLS 官网公开）。可通过 `httpx` 定期从 FRED API `GET https://fred.stlouisfed.org/releases/dates` 拉取（无需 API Key 查部分公开数据）。
- **财报事件**：调用 Alpha Vantage 免费接口 `EARNINGS_CALENDAR`（每分钟 25 次，每天 500 次，足够用），或从 `https://finance.yahoo.com/calendar/earnings` 解析（不稳定）。
- **兜底**：内置一批 2026 重要经济日历硬编码数据，保障即使无网络也有内容。

#### Task B3：注册路由

**文件**：`backend/app/api/router.py`

```python
from app.api import calendar as calendar_router
api_router.include_router(calendar_router.router, prefix="/calendar", tags=["Calendar"])
```

#### Task B4：`main.py` import 模型

```python
from app.models.calendar_event import CalendarEvent  # noqa: F401
```

---

### 阶段四：金融日历（前端）

#### Task B5：新建 `pages/Calendar.tsx`

**布局**：
```
[金融日历]                           [+ 添加自定义事件] [抓取最新数据]

[ 全部 | 📊 经济数据 | 💼 财报 | 📌 自定义 ]    [时间范围: 本周 | 本月 | 未来3月]

┌─────────────────────────────────────────────┐
│ 2026-03-25 周三                              │
│  🔴 高  [经济] CPI 数据发布        08:30 EDT  │
│         美国消费者价格指数月度报告             │
│         距今 2天                             │
├─────────────────────────────────────────────┤
│ 2026-03-26 周四                              │
│  🟡 中  [财报] NVDA 财报           AMC        │
│         英伟达 Q4 FY2026 财报               │
│         距今 3天                             │
└─────────────────────────────────────────────┘
```

**关键组件**：
- `EventTypeBadge`：颜色编码 badge（经济=蓝、财报=紫、自定义=绿）
- `ImportanceDot`：高=红、中=黄、低=灰
- `CountdownBadge`：`今天` / `明天` / `N天后` / `已过去`
- `AddEventModal`：创建自定义事件表单

#### Task B6：`App.tsx` + `Layout.tsx` 注册路由和导航

```tsx
// App.tsx
<Route path="/calendar" element={<ProtectedRoute><Calendar /></ProtectedRoute>} />

// Layout.tsx navItems
{ to: '/calendar', icon: CalendarDays, label: '金融日历' }
```

#### Task B7：`api/index.ts` 新增 `calendarApi`

```typescript
export const calendarApi = {
  list: (params: { start?: string; end?: string; event_type?: string } = {}) =>
    client.get('/calendar/', { params }),
  create: (data: { title: string; event_type: string; event_date: string; description?: string; importance?: string }) =>
    client.post('/calendar/', data),
  update: (id: number, data: Partial<{ title: string; description: string; event_date: string }>) =>
    client.put(`/calendar/${id}`, data),
  remove: (id: number) => client.delete(`/calendar/${id}`),
  fetch: () => client.post('/calendar/fetch'),
}
```

---

## 关键文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `backend/app/skills/engine.py` | 修改 | 新增 `generate_twitter_digest()` |
| `backend/app/scheduler.py` | 修改 | 新增 `job_twitter_digest` 每天 09:00 |
| `backend/app/api/reports.py` | 修改 | 支持 `report_type` 过滤参数 |
| `backend/app/api/reports.py` | 修改 | 新增 `POST /generate-twitter-digest` 端点 |
| `backend/app/models/calendar_event.py` | 新建 | CalendarEvent ORM 模型 |
| `backend/app/api/calendar.py` | 新建 | 金融日历 CRUD + 抓取端点 |
| `backend/app/api/router.py` | 修改 | 注册 calendar 路由 |
| `backend/app/main.py` | 修改 | import CalendarEvent 触发建表 |
| `frontend/src/pages/TwitterTracking.tsx` | 修改 | 新增"观点日报"标签页 |
| `frontend/src/pages/Calendar.tsx` | 新建 | 金融日历页面 |
| `frontend/src/App.tsx` | 修改 | 新增 /calendar 路由 |
| `frontend/src/components/Layout.tsx` | 修改 | 新增金融日历侧边栏入口 |
| `frontend/src/api/index.ts` | 修改 | 新增 calendarApi，扩展 reportsApi |

---

## 风险与缓解

| 风险 | 缓解措施 |
|---|---|
| Alpha Vantage 免费额度耗尽 | 每天仅抓取一次财报数据，结果缓存到 DB；降级为手动录入 |
| Twitter 无推文（未启用追踪） | `generate_twitter_digest()` 检测空数据直接返回，不报错不写 DB |
| FOMC/CPI 日期变更 | 内置硬编码数据仅作兜底；抓取端点定期更新覆盖 |
| CalendarEvent 跨时区 | 所有时间存 UTC，前端用 `date-fns` 转本地时区展示 |
| `report_type` 字段现有 DB 无 `twitter_digest` | `DailyReport` 表 `report_type` 列是 String，无枚举约束，直接写入即可 |

---

## 实施顺序建议

1. Task A1-A3（Twitter 日报后端）—— 约 60 行改动，风险最低
2. Task A4-A5（Twitter 日报前端）—— 在现有页面加 tab
3. Task B1-B4（金融日历后端）—— 新表 + 新路由
4. Task B5-B7（金融日历前端）—— 新页面

---

## SESSION_ID

- CODEX_SESSION: N/A（外部工具不可用，由 Claude 直接执行）
- GEMINI_SESSION: N/A
