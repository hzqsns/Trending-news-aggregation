# 📋 实施计划：多 Agent 平台架构重构 (v2 — 三方审查修订版)

> 综合 Claude Opus 自审 + Codex 后端审查 + Gemini 前端审查的修订版本。
> 相比 v1 主要变更：砍 EventBus、简化 DB 方案、加 Phase 0、扁平化目录、修正移动端 UX。

## 任务类型
- [x] 全栈 (→ 并行)

## 技术方案

### 核心决策

| 决策点 | 结论 | 理由 |
|--------|------|------|
| 微前端 vs 模块化单体 | **模块化单体** | 1-2 人团队，Module Federation 过重；页面零耦合，lazy route groups 足够 |
| 后端分层 | **两层架构**：Platform + Agents（共享模块扁平放置） | 去掉 infrastructure 中间层，减少目录嵌套 |
| DB 策略 | **现有表加 `agent_key` 列** | 比 content+overlay 双表简单，2 个 Agent 场景下重复存储代价可忽略 |
| 前端 Agent 切换 | **侧边栏顶部切换器**（桌面）+ **底部 Tab Bar**（移动端） | 避免 Discord 式双侧边栏在移动端的"嵌套菜单"问题 |
| 设计模式 | Registry + Strategy + Plugin + Adapter | 砍掉 Observer/EventBus，通知继续直接调用 |
| AgentRegistry | **静态注册** | 不做动态插件发现/manifest DSL，显式 Python 代码注册两个 Agent |
| AgentLauncher | **不建** | 默认跳转 last-used Agent（localStorage 持久化），省掉不必要的中间页 |
| SQLite 并发 | **启用 WAL 模式 + busy_timeout** | 多 Agent 并发写入的前置保障 |

### 设计模式分析

```
┌──────────────────────────────────────────────────────────────┐
│                    Platform Layer                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐ │
│  │ AgentRegistry│  │SchedulerKernel│ │  ScopedConfig       │ │
│  │ (Registry)   │  │ (per-agent    │ │  (per-agent 设置)   │ │
│  │ 静态注册     │  │  job register)│ │                     │ │
│  └─────────────┘  └──────────────┘  └─────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│              Shared Modules (扁平放置)                        │
│  ┌───────────┐  ┌────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ crawlers/ │  │  ai/   │  │notifiers/│  │ auth/ + DB   │ │
│  │ (Plugin + │  │(Adapter)│ │(Strategy)│  │              │ │
│  │  Adapter) │  │         │ │ 直接调用  │  │              │ │
│  └───────────┘  └────────┘  └──────────┘  └──────────────┘ │
├──────────────────────────────────────────────────────────────┤
│                    Agent Modules                              │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │  Investment Agent    │  │   Tech Info Agent            │   │
│  │  - skills.py         │  │   - skills.py                │   │
│  │  - jobs.py           │  │   - jobs.py                  │   │
│  │  - routes.py         │  │   - routes.py                │   │
│  │  - defaults.py       │  │   - defaults.py              │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 后端目标目录结构（扁平化）

```
backend/app/
├── platform/
│   ├── registry.py          # AgentRegistry: register/get/list_agents (静态)
│   ├── manifest.py          # AgentManifest dataclass
│   ├── scheduler.py         # SchedulerKernel: 共享调度 + per-agent job 注册
│   └── config.py            # ScopedConfig: 按 agent_key 命名空间的配置服务
├── crawlers/                # 原 sources/ 重构（扁平，不套 infrastructure/）
│   ├── base.py              # CrawlerPlugin ABC (替代 NewsSource)
│   ├── rss.py               # 通用 RSS 爬虫
│   ├── twitter.py           # Twitter 爬虫
│   ├── coingecko.py         # CoinGecko 行情
│   ├── newsapi.py           # NewsAPI
│   ├── github.py            # [新] GitHub Trending
│   ├── v2ex.py              # [新] V2EX
│   ├── linux_do.py          # [新] Linux.do
│   ├── hackernews.py        # [新] HackerNews API
│   └── manager.py           # CrawlerManager: 按 Agent 配置组装爬虫集
├── ai/                      # 不变
├── notifiers/               # 不变（继续直接调用，不引入 EventBus）
├── agents/
│   ├── investment/          # 投研 Agent
│   │   ├── __init__.py      # register_investment_agent()
│   │   ├── skills.py        # 投研 Skills（评分、日报、异常检测）
│   │   ├── jobs.py          # 投研定时任务
│   │   ├── routes.py        # 投研 API 路由
│   │   └── defaults.py      # 内置 Skills、默认设置、RSS feed list
│   └── tech_info/           # 技术信息 Agent
│       ├── __init__.py      # register_tech_info_agent()
│       ├── skills.py        # 技术趋势分析、项目评分
│       ├── jobs.py          # 定时抓取
│       ├── routes.py        # Tech API 路由
│       └── defaults.py      # 内置配置、爬虫列表
├── models/                  # 现有表 + agent_key 列
├── api/                     # 不变，兼容期保留
├── auth.py                  # 不变
├── database.py              # 添加 WAL 模式 + busy_timeout
└── main.py                  # 平台启动 → 注册 Agents
```

### 前端目标结构

```
frontend/src/
├── config/
│   └── agents.ts            # AgentManifest[] 定义
├── components/
│   ├── Layout.tsx            # 重构: AgentProvider 驱动动态导航
│   ├── AgentSwitcher.tsx     # [新] 桌面: 侧边栏顶部下拉; 移动: 底部 Tab
│   └── ui/                   # [新] 共享组件 (Button, Card, Modal, Table...)
├── pages/
│   ├── invest/               # 投研 Agent 页面（现有迁移）
│   │   ├── Dashboard.tsx
│   │   ├── NewsFeed.tsx
│   │   ├── ... (其余 9 页)
│   │   └── TwitterTracking.tsx
│   ├── tech/                 # 技术信息 Agent 页面
│   │   ├── Dashboard.tsx
│   │   ├── GithubTrending.tsx
│   │   ├── TechTwitter.tsx
│   │   ├── V2exFeed.tsx
│   │   ├── LinuxDoFeed.tsx
│   │   └── HackerNews.tsx
│   └── shared/               # 共享页面
│       ├── Login.tsx
│       └── Settings.tsx
├── stores/
│   ├── auth.ts               # 不变
│   ├── theme.ts              # 不变
│   └── agent.ts              # [新] 当前 Agent 状态 (persist last-used)
└── api/
    ├── client.ts             # 不变
    ├── invest/               # 投研 API（现有迁移）
    └── tech/                 # 技术信息 API
```

### AgentManifest 定义

```python
# backend
@dataclass
class AgentManifest:
    key: str                          # "investment", "tech_info"
    name: str                         # "投研 Agent", "技术信息 Agent"
    description: str
    icon: str                         # emoji or icon key
    crawler_plugins: list[str]        # ["rss", "coingecko", "twitter"]
    skill_slugs: list[str]            # 该 Agent 拥有的 Skills
    job_specs: list[JobSpec]          # 定时任务列表
    router: APIRouter                 # Agent 专属路由
    default_settings: dict[str, str]  # Agent 默认配置
```

```typescript
// frontend — 主题色用 CSS 变量，不硬编码 hex
interface AgentManifest {
  id: string
  name: string
  pathPrefix: string              // "/invest", "/tech"
  icon: LucideIcon
  cssVarOverrides: Record<string, string>  // {"--color-agent-primary": "..."}
  navItems: NavItem[]
  description: string
}
```

### 数据库变更（简化方案：加列，不建新表）

| 变更 | 说明 | 风险 |
|------|------|------|
| `articles` 加 `agent_key` 列 | 默认 `'investment'`，唯一约束改为 `(agent_key, url)` | 低 |
| `daily_reports` 加 `agent_key` 列 | 唯一约束改为 `(agent_key, report_type, report_date)` | 低 |
| `alerts` 加 `agent_key` 列 | Agent 级别告警隔离 | 低 |
| `skills` 加 `agent_key` 列 | slug 唯一约束改为 `(agent_key, slug)` | 低 |
| `sentiment_snapshots` 加 `agent_key` 列 | per-agent 情绪快照 | 低 |
| `system_settings` 加 `agent_key` 列 | 唯一约束改为 `(agent_key, key)`，`agent_key=NULL` 表示全局 | 中，需兼容层 |
| `database.py` 启用 WAL | `connect_args={"check_same_thread": False}` + PRAGMA WAL + busy_timeout | 低 |

**push 状态语义**：`is_pushed` 为 per-agent 状态（跟随 articles.agent_key），每个 Agent 独立推送。

### Postgres 退出触发条件

当出现以下任一情况时，应迁移到 PostgreSQL：
- 频繁 "database is locked" 错误
- Agent 数量 > 5
- 需要多进程部署
- 需要更强的并发写入保证

## 实施步骤（5 Phase，13 步）

### Phase 0：回归基线（必须前置）

1. **收集基线指标** — 记录当前系统的关键数据
   - fetch 计数（每次采集的文章数）
   - 评分成功率（ai_analysis 非空比例）
   - 报告生成成功率
   - 推送计数（每日推送条数）
   - 预期产物：`tests/baseline.py` 或手动记录的数据快照

2. **定义 rollback 规则** — 每个 Phase 的回退方案
   - Phase 1: git revert 即可（纯包装，不改 schema）
   - Phase 2: DROP COLUMN（SQLite 需 recreate table，备份 .db 文件）
   - Phase 3: 恢复 sources/ 目录
   - 预期产物：rollback checklist 文档

### Phase 1：平台骨架（零行为变更）

3. **SQLite WAL 模式** — database.py 添加 PRAGMA journal_mode=WAL + busy_timeout=5000
   - 预期产物：修改 `database.py`

4. **创建 `platform/` 目录** — AgentRegistry (静态), AgentManifest, SchedulerKernel
   - 预期产物：3 个文件，纯定义，不改现有行为

5. **包装投研 Agent** — 薄 wrapper 委托到现有 sources/skills/scheduler/routes
   - 预期产物：`agents/investment/`，所有函数直接 import 调用现有代码
   - **关键约束**：wrapper 不引入 scoped config、不改 persistence 路径、不改 schema

6. **main.py 集成** — 通过 AgentRegistry 注册，但实际执行路径不变
   - 预期产物：修改 `main.py`
   - **验证**：对比 Phase 0 基线指标，差异 < 1%

### Phase 2：DB Agent 隔离 + 前端共享 UI

7. **添加 `agent_key` 列** — articles、reports、alerts、skills、sentiment、settings
   - 预期产物：ALTER TABLE + 现有数据默认 `'investment'`
   - 所有 API 查询加 `WHERE agent_key = :current_agent` 过滤
   - **通知双跑策略**：迁移期间 notifier 同时查旧路径和新路径，确保不遗漏不重复

8. **前端共享 UI 组件提取** — 在写任何新页面之前完成
   - 从现有 13 页提取 Button, Card, Table, Modal, Input 到 `components/ui/`
   - 预期产物：`components/ui/` 目录 + 现有页面逐步引用

### Phase 3：共享爬虫层 + 前端 Agent 架构

9. **重构 sources/ → crawlers/** — 提取 CrawlerPlugin ABC，现有 4 个 source 适配
   - 预期产物：`crawlers/` 目录
   - CrawlerManager 按 Agent 的 `crawler_plugins` 配置组装爬虫集

10. **新增爬虫** — GitHub Trending, V2EX, Linux.do, HackerNews
    - 预期产物：4 个新爬虫文件

11. **前端 Agent 架构** — AgentManifest + AgentProvider + 动态导航 + 路由命名空间
    - `config/agents.ts` 定义两个 Agent
    - `stores/agent.ts` 持久化 last-used Agent
    - Layout.tsx 重构：动态 navItems + AgentSwitcher（桌面侧边栏顶部下拉 / 移动端底部 Tab）
    - App.tsx: `/invest/*` 和 `/tech/*` 命名空间，旧路由 redirect 兼容
    - 现有 13 页移入 `pages/invest/`
    - 预期产物：前端架构就绪，投研 Agent 功能不变

### Phase 4：Tech Info Agent

12. **TechInfoAgent 后端** — skills + jobs + routes + defaults
    - 预期产物：`agents/tech_info/`
    - 技术趋势评分 skill、每日技术摘要 skill
    - 定时任务：GitHub/V2EX/Linux.do/HN 采集 + 评分

13. **Tech Info 前端页面** — 6 个页面
    - 预期产物：`pages/tech/` 目录
    - Dashboard (技术热度概览)
    - GithubTrending (按语言/时间范围)
    - TechTwitter (技术大 V 追踪)
    - V2exFeed (热门节点)
    - LinuxDoFeed (精华帖)
    - HackerNews (Top/New/Ask/Show)

## 关键文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/database.py` | 修改 | WAL 模式 + busy_timeout |
| `backend/app/platform/registry.py` | 新建 | AgentRegistry (静态注册) |
| `backend/app/platform/manifest.py` | 新建 | AgentManifest dataclass |
| `backend/app/platform/scheduler.py` | 新建 | SchedulerKernel |
| `backend/app/platform/config.py` | 新建 | ScopedConfigService |
| `backend/app/agents/investment/__init__.py` | 新建 | InvestmentAgent 薄 wrapper |
| `backend/app/agents/investment/skills.py` | 新建 | 委托现有 engine.py |
| `backend/app/agents/investment/jobs.py` | 新建 | 委托现有 scheduler jobs |
| `backend/app/agents/investment/routes.py` | 新建 | 委托现有 API routers |
| `backend/app/agents/investment/defaults.py` | 新建 | 内置 Skills 定义 + RSS feed list |
| `backend/app/agents/tech_info/*` | 新建 | TechInfoAgent 全套 |
| `backend/app/crawlers/base.py` | 新建 | CrawlerPlugin ABC |
| `backend/app/crawlers/github.py` | 新建 | GitHub Trending 爬虫 |
| `backend/app/crawlers/v2ex.py` | 新建 | V2EX 爬虫 |
| `backend/app/crawlers/linux_do.py` | 新建 | Linux.do 爬虫 |
| `backend/app/crawlers/hackernews.py` | 新建 | HackerNews API 爬虫 |
| `backend/app/crawlers/manager.py` | 新建 | CrawlerManager |
| `backend/app/main.py` | 修改 | AgentRegistry 集成 |
| `backend/app/models/*.py` | 修改 | 添加 agent_key 列 |
| `frontend/src/config/agents.ts` | 新建 | AgentManifest 定义 |
| `frontend/src/stores/agent.ts` | 新建 | 当前 Agent 状态 (persist last-used) |
| `frontend/src/components/AgentSwitcher.tsx` | 新建 | Agent 切换组件 |
| `frontend/src/components/ui/*.tsx` | 新建 | 共享 UI 组件库 |
| `frontend/src/components/Layout.tsx` | 修改 | 动态导航 |
| `frontend/src/App.tsx` | 修改 | Agent 路由命名空间 |
| `frontend/src/pages/invest/*.tsx` | 移动 | 现有页面归类 |
| `frontend/src/pages/tech/*.tsx` | 新建 | Tech Info 6 页 |

## 风险与缓解

| 风险 | 严重度 | 缓解措施 |
|------|--------|----------|
| 现有投研功能回归 | 高 | Phase 0 基线 + Phase 1 薄 wrapper + 基线对比验证 |
| DB 迁移数据丢失 | 高 | ALTER TABLE ADD COLUMN + 默认值 + .db 备份 |
| 通知重复/遗漏 | 中 | 迁移期双跑策略：同时查旧新路径，日志比对 |
| SQLite 写锁竞争 | 中 | WAL 模式 + busy_timeout + 短事务 + Postgres 退出触发条件 |
| 路由重定向遗漏 | 中 | 旧路由全部 redirect 到 `/invest/*` |
| 移动端双侧边栏 | 中 | 桌面用侧边栏顶部下拉，移动端用底部 Tab Bar |
| 爬虫反爬/限流 | 中 | 每个爬虫独立 rate limiter + retry + 降级 |
| 前端 bundle 膨胀 | 低 | React.lazy + Vite code splitting，per-agent chunk |
| UI 碎片化 | 中 | Phase 2 强制前置 UI 组件提取，Tech 页面复用 |

## 与 v1 计划的差异

| 项目 | v1 | v2 (本版) | 原因 |
|------|----|-----------|----|
| Phase 数 | 6 Phase 17 步 | 5 Phase 13 步 | 砍 EventBus，合并步骤 |
| EventBus | Phase 6 实施 | **删除** | 2 Agent + 3 notifier，直接调用足够 |
| DB 方案 | content_items + agent_content 双表 | **现有表加 agent_key 列** | 2 Agent 重复存储代价可忽略 |
| 目录结构 | infrastructure/crawling/ 嵌套 | **crawlers/ 扁平** | 去掉 infrastructure 中间层 |
| Agent 切换 UX | Discord 式 App Bar | **桌面下拉 + 移动底部 Tab** | 避免移动端嵌套菜单 |
| AgentLauncher | 有 | **删除** | 默认 last-used Agent |
| Phase 0 | 无 | **新增** | 回归基线 + rollback 规则 |
| SQLite | 未提及 | **WAL + busy_timeout** | 多 Agent 并发写入保障 |
| AgentRegistry | 通用动态 | **静态注册** | 小团队不需要插件发现框架 |
| 前端主题色 | primaryColor hex | **CSS 变量** | WCAG 合规 |
| 共享 UI | Phase 4 | **Phase 2 前置** | 必须在写新页面之前完成 |

## SESSION_ID（供 /ccg:execute 使用）
- CODEX_SESSION: 019d5852-ca48-7503-ac73-4b39ef3a6d47
- GEMINI_SESSION: 983f4e39-a1f5-46f0-aae9-cdc8c644048d
