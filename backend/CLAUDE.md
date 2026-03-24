[根目录](../CLAUDE.md) > **backend**

# backend — FastAPI 后端模块

## 变更记录 (Changelog)

| 日期 | 版本 | 变更说明 |
|---|---|---|
| 2026-03-23 | v2.1 | 初始文档生成；记录 Twitter、书签、Anthropic 格式 AI 客户端等新功能 |

---

## 模块职责

FastAPI 异步后端。负责：新闻采集与去重、LLM 批量评分、定时报告生成、告警检测、多渠道推送、REST API 服务，以及 WebSocket 实时广播。

---

## 入口与启动

| 文件 | 说明 |
|---|---|
| `app/main.py` | FastAPI 应用实例，lifespan 钩子（init DB → init admin user → init settings → init builtin skills → start scheduler） |
| `app/config.py` | Pydantic BaseSettings，从 `.env` 加载；所有默认值在此定义 |
| `app/database.py` | SQLAlchemy async engine + `async_session` 工厂 + `JSONField` 自定义类型 + `init_db()` |
| `app/scheduler.py` | APScheduler AsyncIOScheduler，8 个任务，`start_scheduler()` / `stop_scheduler()` |
| `app/auth.py` | JWT 创建/验证（HS256，7 天），bcrypt 密码哈希，`get_current_user` FastAPI 依赖 |

启动命令（手动）：

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET /health` → `{"status": "ok", "version": "2.0.0"}`

---

## 对外接口（API 路由）

所有路由均以 `/api` 为前缀，定义于 `app/api/router.py`。

| 前缀 | 文件 | 主要端点 |
|---|---|---|
| `/api/auth` | `auth_routes.py` | `POST /login`（返回 JWT token） |
| `/api/articles` | `articles.py` | `GET /`（分页列表，支持 category/source/importance_min/search/hours 过滤）、`GET /trending`、`GET /{id}`、`GET /sources`、`GET /categories` |
| `/api/bookmarks` | `bookmarks.py` | `GET /`（分页，支持 tag/search 过滤）、`POST /`、`PUT /{article_id}`、`DELETE /{article_id}`、`GET /tags`、`GET /status`（批量状态查询，最多 100 条）|
| `/api/dashboard` | `dashboard.py` | `GET /overview`、`GET /sentiment/history`、`GET /stats` |
| `/api/reports` | `reports.py` | `GET /`、`GET /latest`、`GET /{id}`、`POST /generate` |
| `/api/alerts` | `alerts.py` | `GET /`、`GET /active`、`PUT /{id}/resolve` |
| `/api/skills` | `skills.py` | CRUD（`GET /`、`GET /{id}`、`POST /`、`PUT /{id}`、`DELETE /{id}`） |
| `/api/settings` | `settings.py` | `GET /`、`PUT /{key}`、`PUT /`（批量）、`GET /categories`、`GET /ai-providers`、`POST /test-ai` |
| `/api/twitter` | `twitter.py` | `GET /handles`、`POST /handles`、`DELETE /handles/{handle}`、`POST /fetch`、`POST /test-auth`、`POST /import-cookies` |
| `/api/ws/news` | `ws.py` | WebSocket endpoint；广播 `new_article` / `new_alert` 事件 |

所有非 auth/ws 端点均需要有效 JWT（`Depends(get_current_user)`）。

---

## 关键依赖与配置

### Python 依赖（`requirements.txt`）

| 包 | 版本 | 用途 |
|---|---|---|
| `fastapi` | 0.115.6 | Web 框架 |
| `uvicorn[standard]` | 0.34.0 | ASGI 服务器 |
| `sqlalchemy` | 2.0.36 | ORM（异步） |
| `aiosqlite` | 0.20.0 | SQLite 异步驱动 |
| `httpx` | 0.28.1 | 异步 HTTP 客户端（LLM 调用、RSS 抓取）|
| `feedparser` | 6.0.11 | RSS 解析 |
| `apscheduler` | 3.11.0 | 定时任务 |
| `pydantic-settings` | 2.7.1 | 配置管理 |
| `python-jose[cryptography]` | 3.3.0 | JWT |
| `passlib` + `bcrypt` | — | 密码哈希 |
| `websockets` | 14.1 | WebSocket 支持 |
| `twikit` | latest | Twitter/X 非官方客户端 |

### 配置优先级

DB `system_settings` 表 > `backend/.env` 文件 > `config.py` 中的 Pydantic 默认值

---

## 数据模型

SQLite 文件：`backend/data/news_agent.db`（首次启动自动创建，目录自动 mkdir）

| 表名 | 主要字段 | 索引 |
|---|---|---|
| `users` | id, username, hashed_password, is_active | username(unique) |
| `articles` | id, title, url(unique), source, category, importance(0-5), sentiment, ai_analysis(JSON), tags, is_pushed | category, published_at, source, importance |
| `alerts` | id, level(critical/high/medium/low), title, description, skill_name, suggestion, is_active | — |
| `daily_reports` | id, report_type(morning/evening), report_date, title, content(Markdown), key_events(JSON) | report_date + report_type(unique) |
| `skills` | id, name, slug(unique), skill_type, config(JSON), is_builtin, is_enabled | slug(unique) |
| `sentiment_snapshots` | id, snapshot_date, data(JSON) | — |
| `system_settings` | id, key(unique), value, category, label, description, field_type | key(unique) |
| `article_bookmarks` | id, article_id(FK→articles), user_id(FK→users), note, tags(JSON), created_at | user_id; (article_id, user_id) unique |

---

## 子模块说明

### `sources/` — 数据采集

- `base.py`：`NewsItem` dataclass + `NewsSource` ABC（`fetch() -> list[NewsItem]`，`enabled_key` 属性控制开关）
- `rss.py`：`RSSSource`，14 路 RSS feed，feedparser 解析，每源最多取 20 条
- `crypto.py`：`CryptoSource`，CoinGecko API
- `newsapi.py`：`NewsAPISource`，NewsAPI.org（默认关闭，需配置 API Key）
- `twitter.py`：`TwitterSource`，twikit 登录 + cookie 复用，按 handle 列表抓取近 24h 推文
- `manager.py`：`fetch_all_sources()` 并发执行所有启用源，`_save_items()` 去重入库，新文章广播 WebSocket

### `skills/` — AI 引擎

- `engine.py`：
  - `run_importance_scoring()`：查近 24h 未评分文章（最多 50 条），BATCH_SIZE=10 批量调用 LLM，每批一次 API 调用，输出 importance / sentiment / tags / reason
  - `generate_daily_report(type)`：查近期高重要度文章，生成 Markdown 格式早/晚报
  - `run_anomaly_detection()`：查近 1h importance >= 4 文章，创建 Alert 记录

### `ai/` — LLM 客户端

- `client.py`：
  - 支持 6 家服务商预设：openai / deepseek / gemini / openrouter / dashscope / minimax
  - 支持 2 种 API 格式：`openai`（`/chat/completions`）和 `anthropic`（`/v1/messages`）
  - `chat_completion(messages, ...)` → 纯文本
  - `chat_completion_json(messages, ...)` → 自动解析 JSON dict

### `notifiers/` — 推送

- `base.py`：`Notifier` ABC（`send()` / `send_markdown()`）
- `telegram.py`：通过 python-telegram-bot 发送
- `wechat.py`：通过 PushPlus HTTP API 发送
- `qq.py`：通过 Qmsg HTTP API 发送
- `manager.py`：`push_important_news()`、`push_news_digest()`、`push_alert()`；按 DB 设置动态加载启用的 notifier

---

## 测试与质量

- 当前无自动化测试，`test_twikit.py` 已被 `.gitignore` 排除
- 建议：pytest + pytest-asyncio，优先覆盖 `skills/engine.py`（批量评分）和 `api/bookmarks.py`（标签/备注边界）

---

## 常见问题 (FAQ)

**Q: 如何切换 LLM 服务商？**
A: 在 Web UI 系统设置中修改 `ai_provider`（选择预设）或直接修改 `ai_api_base` / `ai_api_key` / `ai_model`。选择 `minimax` 时会自动切换为 Anthropic 格式。

**Q: Twitter 采集失败？**
A: 检查 `twitter_auth_username` / `twitter_auth_password` 是否配置；首次运行需登录，cookies 保存至 `backend/data/twitter_cookies.json`；也可通过 `POST /api/twitter/import-cookies` 导入浏览器 Cookie。

**Q: 数据库 schema 变更后如何更新？**
A: `init_db()` 使用 `create_all(checkfirst=True)`，只新建不存在的表，不会自动迁移列变更。如需 schema 迁移，需手动 ALTER TABLE 或删除 DB 文件重建。

**Q: `ai_analysis` 字段是 None，文章没有评分？**
A: 检查 AI 是否启用（`ai_enabled = true`）、`ai_api_key` 是否有效；查看后端日志中 `Scored X/Y articles` 的输出。

---

## 相关文件清单

```
backend/
├── app/
│   ├── main.py              # 应用入口，lifespan，内置 Skill 初始化
│   ├── config.py            # Pydantic Settings
│   ├── database.py          # SQLAlchemy engine，JSONField
│   ├── scheduler.py         # 8 个定时任务
│   ├── auth.py              # JWT，密码哈希，get_current_user
│   ├── api/
│   │   ├── router.py        # 汇总所有 Router
│   │   ├── auth_routes.py
│   │   ├── articles.py
│   │   ├── bookmarks.py
│   │   ├── dashboard.py
│   │   ├── reports.py
│   │   ├── alerts.py
│   │   ├── skills.py
│   │   ├── settings.py
│   │   ├── twitter.py
│   │   └── ws.py
│   ├── models/
│   │   ├── user.py
│   │   ├── article.py
│   │   ├── alert.py
│   │   ├── report.py
│   │   ├── skill.py
│   │   ├── sentiment.py
│   │   ├── setting.py       # SystemSetting + DEFAULT_SETTINGS (35条)
│   │   └── bookmark.py
│   ├── sources/
│   │   ├── base.py          # NewsItem, NewsSource ABC
│   │   ├── rss.py           # 14 路 RSS
│   │   ├── crypto.py        # CoinGecko
│   │   ├── newsapi.py       # NewsAPI.org
│   │   ├── twitter.py       # twikit
│   │   └── manager.py       # fetch_all_sources, _save_items
│   ├── skills/
│   │   └── engine.py        # run_importance_scoring, generate_daily_report, run_anomaly_detection
│   ├── ai/
│   │   └── client.py        # chat_completion, chat_completion_json, 双格式支持
│   └── notifiers/
│       ├── base.py
│       ├── telegram.py
│       ├── wechat.py
│       ├── qq.py
│       └── manager.py
├── requirements.txt
└── .env.example
```
