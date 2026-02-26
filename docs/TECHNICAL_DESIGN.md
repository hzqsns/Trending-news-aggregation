# 投研 Agent 新闻聚合系统 — 技术设计文档 v2.0

> 版本：v2.0 | 日期：2026-02-23
> 参考：[@xingpt 的 Agent 化投研系统理念](https://x.com/xingpt/status/2025219080421277813)

---

## 一、项目定位重新定义

### v1.0 的问题

v1.0 将项目定义为"新闻聚合网站"——这只是一个**数据搬运工具**。正如 @xingpt 文章指出的：

> "我的时间没有花在投资分析的思考和决策，我只是在做一个数据搬运工。
> 真正需要我判断的决策，可能只占 20% 的时间。剩下 80% 都是重复性的信息收集和整理。"

### v2.0 的重新定位

本项目不是一个新闻网站，而是一个 **投研 Agent 系统**，参考文章中的三层架构：

| 层次 | 职责 | 对应文章概念 |
|------|------|-------------|
| **Knowledge Base（知识库）** | 持续采集、结构化存储全球财经数据 | "Agent 的记忆系统" |
| **Skills（决策框架）** | AI 驱动的分析引擎，按用户定义的框架自动研判 | "把判断标准显性化、结构化" |
| **CRON（自动化执行）** | 定时采集 + 定时分析 + 定时推送 | "让系统真正运转起来" |

**核心差异：v1.0 只做了"采集→展示"，v2.0 在中间加入了"AI 分析研判"这一关键环节。**

---

## 二、整体架构（前后端分离）

```
┌─────────────────────────────────────────────────────────────────────┐
│                          CRON 层（定时调度）                          │
│                                                                     │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ 新闻采集  │  │ AI 分析研判   │  │ 报告生成      │  │ 多渠道推送  │  │
│  │ 每10分钟  │  │ 每次采集后    │  │ 每日早晚各1次 │  │ 实时+定时   │  │
│  └────┬─────┘  └──────┬───────┘  └──────┬───────┘  └─────┬──────┘  │
│       │               │                │                 │         │
└───────┼───────────────┼────────────────┼─────────────────┼─────────┘
        │               │                │                 │
        ▼               ▼                ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Python 后端（FastAPI）                           │
│                                                                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │   Knowledge Base │  │     Skills      │  │   RESTful API      │  │
│  │   知识库管理      │  │   决策框架引擎   │  │   供前端调用        │  │
│  │                  │  │                 │  │                    │  │
│  │ • 新闻/快讯      │  │ • 重要度评分     │  │ GET /api/articles  │  │
│  │ • 宏观数据       │  │ • 情绪分析       │  │ GET /api/dashboard │  │
│  │ • 行情数据       │  │ • 流动性监控     │  │ GET /api/reports   │  │
│  │ • 财报数据       │  │ • 异常预警       │  │ GET /api/alerts    │  │
│  │ • 历史事件复盘   │  │ • 市场日报生成   │  │ WS  /ws/realtime   │  │
│  └────────┬────────┘  └────────┬────────┘  └─────────┬──────────┘  │
│           │                    │                      │             │
│           └────────────┬───────┘                      │             │
│                        ▼                              │             │
│              ┌──────────────────┐                     │             │
│              │   PostgreSQL     │                     │             │
│              │   (主数据库)      │                     │             │
│              └──────────────────┘                     │             │
└───────────────────────────────────────────────────────┼─────────────┘
                                                        │
                                        ┌───────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    React 前端（Vite + TailwindCSS）                  │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│  │ Dashboard │ │ 新闻流   │ │ AI 日报  │ │ 预警中心 │ │ Skills   │ │
│  │ 数据看板  │ │ 实时更新  │ │ 市场解读 │ │ 异常信号 │ │ 配置管理 │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        推送通道                                      │
│  ┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Telegram │  │ 微信(PushPlus)│  │ QQ(Qmsg) │  │ Email/Webhook  │  │
│  └──────────┘  └──────────────┘  └──────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 三、三层架构详细设计

### 3.1 第一层：Knowledge Base（知识库）

参考文章中的知识库设计，我们的系统需要持续采集和结构化以下信息：

#### 3.1.1 数据源矩阵

| 分类 | 数据源 | 采集方式 | 频率 | 数据类型 |
|------|--------|----------|------|----------|
| **财经快讯** | 金十数据 | 爬虫 | 每5分钟 | 实时快讯、经济日历 |
| **财经快讯** | 华尔街见闻 | RSS/爬虫 | 每10分钟 | 7x24快讯 |
| **A股资讯** | 新浪财经 | RSS | 每15分钟 | A股新闻、公告 |
| **A股资讯** | 东方财富 | 爬虫 | 每15分钟 | 研报、热帖、资金流向 |
| **美股资讯** | NewsAPI / Yahoo Finance | API | 每15分钟 | 美股新闻 |
| **加密货币** | CoinGecko / CoinDesk | API/RSS | 每10分钟 | 币圈新闻、行情 |
| **宏观数据** | 美联储/FRED | API | 每日 | 利率、CPI、非农等 |
| **社交舆情** | Twitter/X 关键账号 | API | 每30分钟 | KOL 观点、市场情绪 |
| **科技财经** | 36氪 / 虎嗅 | RSS | 每30分钟 | 科技行业动态 |

#### 3.1.2 知识库存储设计

不同于 v1.0 只有一张 `articles` 表，v2.0 需要多维度的结构化存储：

```
Knowledge Base
├── articles          # 新闻/快讯原文
├── market_data       # 行情数据（指数、个股、加密货币）
├── macro_indicators  # 宏观经济指标（CPI、利率、非农）
├── alerts            # 系统生成的预警信号
├── daily_reports     # AI 生成的每日市场报告
├── event_archive     # 历史重大事件复盘库
└── skills_config     # 用户定义的决策框架
```

---

### 3.2 第二层：Skills（决策框架引擎）

这是 v2.0 **最核心的差异化设计**。参考文章中的 Skill 概念，我们让用户定义自己的判断标准，AI 按照这些标准自动执行分析。

#### 3.2.1 内置 Skills

**Skill 1：新闻重要度评分**

```yaml
skill: news_importance_scorer
input: 一条新闻的标题 + 摘要
判断标准:
  - 是否涉及央行政策变化（美联储/欧央行/日央行） → +3分
  - 是否涉及重大地缘政治事件 → +3分
  - 是否涉及 Top 50 公司财报发布 → +2分
  - 是否涉及加密货币监管政策 → +2分
  - 是否涉及宏观数据发布（CPI/非农/PMI） → +2分
  - 是否是市场异常波动（单日涨跌超3%） → +3分
  - 是否是普通行业新闻 → +0分
output: importance_score (0-5) + 分类标签 + 理由
```

**Skill 2：市场情绪监控**

```yaml
skill: market_sentiment_monitor
input: 近24小时新闻流 + 行情数据
监控指标:
  - 恐慌/贪婪关键词频率统计
  - 涨跌幅分布（个股/板块）
  - 成交量异动
  - 社交媒体情绪倾向
output: 情绪评级（极度贪婪/贪婪/中性/恐慌/极度恐慌）+ 分析理由
```

**Skill 3：每日市场摘要生成**

```yaml
skill: daily_market_summary
input: 当日所有新闻 + 行情数据 + 宏观指标
任务:
  - 筛选 Top 10 最重要事件
  - 生成 overnight 全球市场概览
  - 提炼今日需关注的核心事项
  - 给出简要策略建议
output: 结构化日报（Markdown 格式）
```

**Skill 4：异常预警**

```yaml
skill: anomaly_alert
input: 实时行情 + 宏观数据流
触发条件:
  - 主要指数单日波动超过 2%
  - 关键宏观指标大幅偏离预期
  - 多个流动性指标同时恶化
  - 突发黑天鹅事件关键词出现
output: 预警等级（低/中/高/紧急）+ 事件描述 + 历史类比 + 建议
```

#### 3.2.2 自定义 Skills（用户可配置）

用户可以通过 Web 界面定义自己的 Skill，例如：

```yaml
skill: my_btc_bottom_signal
name: "比特币抄底信号"
input: BTC 行情数据 + 链上数据
判断标准:
  - RSI < 30 且周线级别超跌
  - MVRV 比率 < 1.0
  - 恐慌指数 > 75
  - 长期持有者供应占比上升
触发条件: 满足3个以上指标
output: 抄底评级（强/中/弱）+ 建议仓位比例
```

系统将 Skill 配置存入数据库，运行时通过 LLM 解释并执行这些规则。

---

### 3.3 第三层：CRON（自动化执行）

```
┌────────────────────────────────────────────────────────────────┐
│                        CRON 调度表                              │
│                                                                │
│  ┌─ 高频任务 ──────────────────────────────────────────────┐   │
│  │ • fetch_flash_news()        每 5 分钟   快讯采集         │   │
│  │ • fetch_general_news()      每 15 分钟  新闻采集         │   │
│  │ • check_anomaly_alerts()    每 10 分钟  异常预警扫描     │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─ 中频任务 ──────────────────────────────────────────────┐   │
│  │ • run_sentiment_analysis()  每 1 小时   情绪分析         │   │
│  │ • push_news_digest()        每 30 分钟  汇总推送         │   │
│  │ • fetch_market_data()       每 30 分钟  行情数据         │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─ 低频任务 ──────────────────────────────────────────────┐   │
│  │ • generate_morning_report() 每日 07:30  早间市场日报     │   │
│  │ • generate_evening_report() 每日 22:00  晚间美股日报     │   │
│  │ • fetch_macro_data()        每日 09:00  宏观数据更新     │   │
│  │ • cleanup_old_data()        每日 03:00  清理过期数据     │   │
│  └────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```

---

## 四、前后端分离架构设计

### 4.1 后端：Python + FastAPI（纯 API 服务）

后端只负责数据采集、AI 分析、存储和 API 服务，不渲染任何 HTML。

#### API 设计

```
/api
├── /articles                    # 新闻资讯
│   ├── GET    /                 # 分页列表（支持分类/搜索/时间范围筛选）
│   ├── GET    /:id              # 文章详情
│   └── GET    /trending         # 热门/高重要度文章
│
├── /dashboard                   # 数据看板
│   ├── GET    /overview         # 今日概览（新闻数、预警数、情绪指标）
│   ├── GET    /sentiment        # 市场情绪时间线
│   └── GET    /stats            # 采集统计
│
├── /reports                     # AI 报告
│   ├── GET    /                 # 报告列表
│   ├── GET    /latest           # 最新日报
│   └── GET    /:id              # 报告详情
│
├── /alerts                      # 预警中心
│   ├── GET    /                 # 预警列表
│   └── GET    /active           # 当前活跃预警
│
├── /skills                      # Skills 管理
│   ├── GET    /                 # 所有 Skills 列表
│   ├── POST   /                 # 创建自定义 Skill
│   ├── PUT    /:id              # 更新 Skill
│   ├── DELETE /:id              # 删除 Skill
│   └── POST   /:id/test        # 测试运行 Skill
│
├── /settings                    # 系统设置
│   ├── GET    /sources          # 数据源配置
│   ├── PUT    /sources          # 更新数据源配置
│   ├── GET    /notifications    # 推送渠道配置
│   └── PUT    /notifications    # 更新推送配置
│
└── /ws
    └── /realtime                # WebSocket 实时推送新闻
```

#### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| Web 框架 | FastAPI | 异步、高性能、自动文档 |
| ORM | SQLAlchemy 2.0 (async) | 成熟、支持多数据库 |
| 数据库 | PostgreSQL | 支持全文搜索、JSONB、高并发 |
| 缓存 | Redis | 行情数据缓存、实时推送队列 |
| 任务调度 | APScheduler / Celery | 定时任务 + 异步任务队列 |
| AI 引擎 | OpenAI API 兼容接口 | GPT-4o / DeepSeek / 本地模型均可 |
| HTTP 客户端 | httpx (async) | 异步爬虫 |
| WebSocket | FastAPI WebSocket | 前端实时更新 |

---

### 4.2 前端：React + Vite + TailwindCSS（独立 SPA）

前端作为独立项目，通过 API 与后端通信。

#### 技术选型

| 组件 | 选择 | 理由 |
|------|------|------|
| 框架 | React 19 | 生态最大、组件丰富 |
| 构建工具 | Vite | 快速开发体验 |
| 路由 | React Router v7 | 标准方案 |
| 状态管理 | Zustand | 轻量、简洁 |
| CSS | TailwindCSS 4 | 原子化 CSS、开发效率高 |
| UI 组件库 | shadcn/ui | 高质量、可定制 |
| 图表 | Recharts | 轻量、React 原生 |
| HTTP | Axios / TanStack Query | 数据请求 + 缓存 |
| WebSocket | 原生 WebSocket | 实时数据推送 |

#### 页面规划

| 页面 | 路由 | 功能描述 |
|------|------|----------|
| **Dashboard** | `/` | 数据概览看板：今日新闻数、活跃预警、市场情绪仪表盘、热门新闻 |
| **新闻流** | `/news` | 实时新闻时间线，支持分类/搜索/重要度筛选，WebSocket 实时更新 |
| **AI 日报** | `/reports` | AI 生成的每日市场摘要，早报/晚报切换 |
| **预警中心** | `/alerts` | 异常预警列表，按等级/类型/时间筛选 |
| **Skills 管理** | `/skills` | 查看/创建/编辑/测试决策框架 |
| **系统设置** | `/settings` | 数据源管理、推送渠道配置、采集频率设置 |

#### Dashboard 布局草图

```
┌────────────────────────────────────────────────────────┐
│  [Logo] 投研 Agent          [搜索框]      [设置] [通知] │
├────────┬───────────────────────────────────────────────┤
│        │                                               │
│  导航栏 │  ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│        │  │ 今日新闻   │ │ 活跃预警  │ │ 市场情绪  │      │
│ Dashboard│ │   328     │ │    5     │ │  贪婪 72  │      │
│ 新闻流  │  └──────────┘ └──────────┘ └──────────┘      │
│ AI 日报 │                                               │
│ 预警中心│  ┌─────────────────────────────────────┐      │
│ Skills │  │         市场情绪趋势图（7天）          │      │
│ 设置   │  │     📈 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~   │      │
│        │  └─────────────────────────────────────┘      │
│        │                                               │
│        │  ┌─────────────────┐ ┌─────────────────┐      │
│        │  │  热门新闻 Top10  │ │  最新预警         │      │
│        │  │  1. xxxxxx      │ │  ⚠️ 美债收益率..   │      │
│        │  │  2. xxxxxx      │ │  🔴 BTC 跌破...   │      │
│        │  │  3. xxxxxx      │ │  🟡 A股成交量..    │      │
│        │  │  ...            │ │  ...              │      │
│        │  └─────────────────┘ └─────────────────┘      │
└────────┴───────────────────────────────────────────────┘
```

---

### 4.3 前后端分离 vs SSR 对比

| 维度 | 前后端分离 (React + FastAPI) | SSR (Jinja2 + FastAPI) |
|------|------------------------------|------------------------|
| **用户体验** | 流畅的 SPA 交互，实时更新 | 每次操作刷新页面 |
| **实时推送** | WebSocket 原生支持 | 需额外 JS 实现 |
| **开发效率** | 前后端可并行开发 | 一个人就能搞定 |
| **部署复杂度** | 需部署两个服务 | 单一服务 |
| **扩展性** | 天然支持移动端/第三方对接 | 需额外开发 API |
| **团队要求** | 需要前端能力 | 纯 Python 即可 |

**选择前后端分离的理由：**
1. Dashboard 需要丰富的图表和实时交互，SPA 体验远优于传统页面
2. WebSocket 实时推送是核心需求
3. API 优先设计，后续可直接对接移动端、Telegram Bot、第三方系统
4. Skills 配置页面需要复杂表单交互

**代价：**
- 部署多了一个前端服务（但可以用 Nginx 静态托管，成本极低）
- 需要前端开发能力（但 shadcn/ui 可大幅降低开发量）

---

## 五、数据模型设计（v2.0）

```sql
-- 1. 新闻/快讯
CREATE TABLE articles (
    id            SERIAL PRIMARY KEY,
    title         VARCHAR(500) NOT NULL,
    url           VARCHAR(1000) NOT NULL UNIQUE,
    source        VARCHAR(100) NOT NULL,
    category      VARCHAR(50) DEFAULT 'general',
    summary       TEXT,
    content       TEXT,
    image_url     VARCHAR(1000),
    published_at  TIMESTAMP,
    fetched_at    TIMESTAMP DEFAULT NOW(),
    is_pushed     BOOLEAN DEFAULT FALSE,
    importance    INTEGER DEFAULT 0,
    sentiment     VARCHAR(20),           -- bullish / bearish / neutral
    ai_analysis   JSONB,                 -- AI 分析结果（结构化 JSON）
    tags          TEXT[]                  -- 标签数组
);

-- 2. 预警信号
CREATE TABLE alerts (
    id            SERIAL PRIMARY KEY,
    level         VARCHAR(20) NOT NULL,   -- low / medium / high / critical
    title         VARCHAR(500) NOT NULL,
    description   TEXT NOT NULL,
    skill_id      INTEGER REFERENCES skills(id),
    trigger_data  JSONB,                  -- 触发预警的原始数据
    historical_reference TEXT,            -- 历史类比
    suggestion    TEXT,                   -- 建议操作
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT NOW(),
    resolved_at   TIMESTAMP
);

-- 3. AI 日报
CREATE TABLE daily_reports (
    id            SERIAL PRIMARY KEY,
    report_type   VARCHAR(20) NOT NULL,   -- morning / evening
    report_date   DATE NOT NULL,
    title         VARCHAR(200),
    content       TEXT NOT NULL,           -- Markdown 格式
    key_events    JSONB,                   -- Top 事件列表
    sentiment     JSONB,                   -- 当日情绪数据
    suggestions   JSONB,                   -- 策略建议
    created_at    TIMESTAMP DEFAULT NOW(),
    UNIQUE(report_type, report_date)
);

-- 4. Skills 配置
CREATE TABLE skills (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(100) NOT NULL,
    slug          VARCHAR(100) NOT NULL UNIQUE,
    description   TEXT,
    skill_type    VARCHAR(50) NOT NULL,    -- scorer / monitor / analyzer / generator
    config        JSONB NOT NULL,          -- Skill 的完整配置（YAML 转 JSON）
    is_builtin    BOOLEAN DEFAULT FALSE,
    is_enabled    BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMP DEFAULT NOW(),
    updated_at    TIMESTAMP DEFAULT NOW()
);

-- 5. 宏观经济指标
CREATE TABLE macro_indicators (
    id            SERIAL PRIMARY KEY,
    indicator     VARCHAR(100) NOT NULL,   -- cpi / fed_rate / nonfarm / pmi...
    value         DECIMAL(20, 6),
    previous      DECIMAL(20, 6),
    forecast      DECIMAL(20, 6),
    period        VARCHAR(50),             -- "2026-01" / "2026-Q1"
    released_at   TIMESTAMP,
    source        VARCHAR(100),
    metadata      JSONB
);

-- 6. 市场情绪快照
CREATE TABLE sentiment_snapshots (
    id            SERIAL PRIMARY KEY,
    snapshot_time TIMESTAMP DEFAULT NOW(),
    overall_score INTEGER,                 -- 0-100 (0=极度恐慌, 100=极度贪婪)
    label         VARCHAR(20),             -- extreme_fear / fear / neutral / greed / extreme_greed
    breakdown     JSONB,                   -- 各维度得分明细
    news_volume   INTEGER,                 -- 当前新闻量
    top_keywords  TEXT[]                   -- 高频关键词
);

-- 7. 推送记录
CREATE TABLE push_logs (
    id            SERIAL PRIMARY KEY,
    channel       VARCHAR(50) NOT NULL,    -- telegram / wechat / qq / email
    content_type  VARCHAR(50),             -- alert / digest / report
    content_id    INTEGER,
    status        VARCHAR(20),             -- sent / failed / pending
    sent_at       TIMESTAMP,
    error_message TEXT
);
```

---

## 六、AI 引擎设计

### 6.1 LLM 集成策略

```
┌────────────────────────────────────────┐
│            AI Engine (统一接口)          │
│                                        │
│  ┌──────────┐  ┌──────────┐            │
│  │ OpenAI   │  │ DeepSeek │  ← 可切换  │
│  │ GPT-4o   │  │ V3       │            │
│  └──────────┘  └──────────┘            │
│  ┌──────────┐  ┌──────────┐            │
│  │ Claude   │  │ 本地模型  │  ← 可扩展  │
│  │ Sonnet   │  │ Ollama   │            │
│  └──────────┘  └──────────┘            │
└────────────────────────────────────────┘
```

**成本控制策略：**

| 任务类型 | 推荐模型 | 单次成本估算 | 日调用次数 |
|----------|----------|-------------|-----------|
| 新闻重要度评分 | GPT-4o-mini / DeepSeek | ~$0.001 | ~500次 |
| 情绪分析 | GPT-4o-mini | ~$0.003 | ~24次 |
| 日报生成 | GPT-4o / Claude Sonnet | ~$0.05 | 2次 |
| 异常预警分析 | GPT-4o | ~$0.02 | ~10次 |
| **日均总成本** | | | **~$1.5-3** |

参考文章中提到的 **"每月 API 调用费 500 美金"** 是一个更复杂的系统。我们的初期版本控制在 **$50-100/月** 完全可行。

### 6.2 Prompt 工程

每个 Skill 本质上是一个**结构化 Prompt 模板**，系统会将 Skill 配置 + 实时数据 组装成完整的 Prompt 发送给 LLM：

```
System: 你是一个专业的投研分析 Agent。以下是你的分析框架：
{skill.config 内容}

User: 请基于以下数据进行分析：
{实时数据 / 新闻内容}

请严格按照以下格式输出：
{输出格式定义}
```

---

## 七、推送系统设计（v2.0 增强版）

### 7.1 推送策略矩阵

| 事件类型 | 推送时机 | 推送格式 | 渠道 |
|----------|----------|----------|------|
| 紧急预警 (critical) | **立即** | 单条：标题+描述+建议 | 全渠道 |
| 高级预警 (high) | **立即** | 单条：标题+描述 | Telegram + 微信 |
| AI 早报 | 每日 07:30 | 完整日报 | 全渠道 |
| AI 晚报 | 每日 22:00 | 完整日报 | 全渠道 |
| 新闻摘要 | 每 30 分钟 | 聚合摘要（5-10条） | Telegram |
| Skill 触发通知 | 触发时 | 自定义格式 | 用户配置的渠道 |

### 7.2 推送渠道对比

| 渠道 | 实现方式 | 优点 | 缺点 | 推荐指数 |
|------|----------|------|------|----------|
| **Telegram** | Bot API | 最强：富文本、按钮、图片、Bot 交互 | 国内需科学上网 | ★★★★★ |
| **微信** | PushPlus | 简单接入，扫码绑定 | 免费每天200条，格式受限 | ★★★★ |
| **QQ** | Qmsg | 接入简单 | 功能有限，生态不稳定 | ★★★ |
| **Email** | SMTP | 支持富文本和附件 | 时效性差 | ★★★ |
| **Webhook** | HTTP POST | 灵活，可对接任何系统 | 需要接收端 | ★★★★ |

### 7.3 Telegram Bot 交互扩展（后期）

不仅推送，还可以通过 Telegram Bot 进行交互查询：

```
用户发送:  /report         → 获取最新日报
用户发送:  /alert          → 查看当前活跃预警
用户发送:  /news crypto    → 查看最新加密货币新闻
用户发送:  /sentiment      → 查看当前市场情绪
用户发送:  /ask 美联储最新动态  → AI 回答问题
```

---

## 八、项目目录结构（v2.0 前后端分离）

```
Trending-news-aggregation/
│
├── backend/                          # Python 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 入口 + 生命周期
│   │   ├── config.py                 # 配置管理
│   │   ├── database.py               # 数据库连接
│   │   │
│   │   ├── models/                   # 数据模型
│   │   │   ├── article.py
│   │   │   ├── alert.py
│   │   │   ├── report.py
│   │   │   ├── skill.py
│   │   │   ├── macro.py
│   │   │   └── sentiment.py
│   │   │
│   │   ├── api/                      # API 路由
│   │   │   ├── articles.py
│   │   │   ├── dashboard.py
│   │   │   ├── reports.py
│   │   │   ├── alerts.py
│   │   │   ├── skills.py
│   │   │   └── settings.py
│   │   │
│   │   ├── sources/                  # 数据采集插件
│   │   │   ├── base.py
│   │   │   ├── rss.py
│   │   │   ├── jin10.py
│   │   │   ├── eastmoney.py
│   │   │   ├── crypto.py
│   │   │   ├── newsapi.py
│   │   │   └── twitter.py
│   │   │
│   │   ├── skills/                   # AI 决策框架引擎
│   │   │   ├── engine.py             # Skill 执行引擎
│   │   │   ├── scorer.py             # 重要度评分
│   │   │   ├── sentiment.py          # 情绪分析
│   │   │   ├── anomaly.py            # 异常预警
│   │   │   └── reporter.py           # 日报生成
│   │   │
│   │   ├── notifiers/                # 推送插件
│   │   │   ├── base.py
│   │   │   ├── telegram.py
│   │   │   ├── wechat.py
│   │   │   ├── qq.py
│   │   │   └── webhook.py
│   │   │
│   │   ├── ai/                       # AI 引擎
│   │   │   ├── client.py             # LLM 客户端（多模型支持）
│   │   │   └── prompts.py            # Prompt 模板
│   │   │
│   │   └── scheduler.py              # CRON 调度器
│   │
│   ├── alembic/                      # 数据库迁移
│   ├── tests/                        # 测试
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                         # React 前端
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/                      # API 调用层
│   │   │   ├── client.ts
│   │   │   ├── articles.ts
│   │   │   ├── dashboard.ts
│   │   │   ├── reports.ts
│   │   │   └── alerts.ts
│   │   ├── pages/                    # 页面组件
│   │   │   ├── Dashboard.tsx
│   │   │   ├── NewsFeed.tsx
│   │   │   ├── Reports.tsx
│   │   │   ├── Alerts.tsx
│   │   │   ├── Skills.tsx
│   │   │   └── Settings.tsx
│   │   ├── components/               # 通用组件
│   │   │   ├── Layout.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── NewsCard.tsx
│   │   │   ├── AlertBadge.tsx
│   │   │   ├── SentimentGauge.tsx
│   │   │   └── ...
│   │   ├── hooks/                    # 自定义 Hooks
│   │   ├── stores/                   # Zustand 状态
│   │   └── lib/                      # 工具函数
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── Dockerfile
│
├── docker-compose.yml                # 一键部署
├── nginx.conf                        # 反向代理
└── README.md
```

---

## 九、部署方案（Docker Compose 一键部署）

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/news_agent
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  frontend:
    build: ./frontend
    ports:
      - "3000:80"

  db:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=news_agent
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

  redis:
    image: redis:7-alpine

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf

volumes:
  pgdata:
```

**部署成本估算：**

| 方案 | 配置 | 月成本 |
|------|------|--------|
| 最低配 VPS | 2C4G | ¥50-80/月 |
| 推荐配置 | 4C8G | ¥100-200/月 |
| AI API 费用 | GPT-4o-mini 为主 | $50-100/月 |
| **总计** | | **¥500-1000/月** |

---

## 十、开发阶段规划

### Phase 1：MVP（2-3 周）
- [x] 项目骨架搭建
- [ ] 3-5 个核心新闻源接入（RSS + API）
- [ ] 基础数据库和 API
- [ ] 新闻重要度评分 Skill
- [ ] React 前端：新闻列表页 + Dashboard
- [ ] Telegram 推送

### Phase 2：智能分析（2-3 周）
- [ ] 市场情绪分析 Skill
- [ ] AI 每日市场日报生成
- [ ] 异常预警系统
- [ ] 前端：AI 日报页、预警中心
- [ ] 微信 / QQ 推送

### Phase 3：高级功能（3-4 周）
- [ ] 自定义 Skills 配置界面
- [ ] 宏观经济数据采集
- [ ] WebSocket 实时推送到前端
- [ ] Telegram Bot 交互查询
- [ ] 历史事件复盘库

### Phase 4：优化 & 扩展
- [ ] 性能优化、缓存策略
- [ ] 更多数据源接入
- [ ] 移动端适配 / PWA
- [ ] 多用户支持
- [ ] 部署文档和 CI/CD

---

## 十一、风险分析（v2.0 更新）

| 风险 | 严重度 | 概率 | 缓解措施 |
|------|--------|------|----------|
| AI API 成本超预期 | 高 | 中 | 分级使用模型：小任务用 mini，大任务用 4o；设置日预算上限 |
| LLM 幻觉导致错误分析 | 高 | 中 | Skill 输出需结构化校验；重要预警需人工确认 |
| 爬虫被封 | 中 | 高 | 优先 RSS/API；IP 代理池；尊重 robots.txt |
| 第三方推送服务变更 | 中 | 中 | 插件化架构；多渠道冗余 |
| 前端开发工作量大 | 中 | 低 | 使用 shadcn/ui 组件库；优先核心页面 |
| 数据合规/法律风险 | 高 | 低 | 不存储全文；标注来源；遵守各站 TOS |

---

## 十二、v1.0 vs v2.0 对比总结

| 维度 | v1.0 新闻聚合站 | v2.0 投研 Agent 系统 |
|------|-----------------|---------------------|
| **定位** | 新闻搬运工具 | 智能投研助手 |
| **核心能力** | 采集 + 展示 | 采集 + AI分析 + 预警 + 推送 |
| **前端** | Jinja2 SSR（一体化） | React SPA（前后端分离） |
| **数据库** | SQLite（单表） | PostgreSQL（多表 + JSONB） |
| **AI** | 可选的摘要功能 | 核心引擎（评分/情绪/预警/日报） |
| **Skills** | 无 | 内置 + 用户自定义决策框架 |
| **交互性** | 静态页面 | 实时更新 + WebSocket + Bot 交互 |
| **扩展性** | 低 | 高（API 优先，可对接任意客户端） |
| **部署复杂度** | 低（单服务） | 中（多服务 Docker Compose） |
| **开发周期** | 1-2 周 | 6-10 周（分阶段） |
| **月运营成本** | ¥30-50 | ¥500-1000 |

---

> **总结：** v2.0 方案的核心理念来自 @xingpt 文章——**用算法复制你的判断框架，用 API 成本替代人力成本**。系统不仅是一个信息采集器，更是一个能按照你定义的决策框架自动运行的投研 Agent。前后端分离架构确保了系统的可扩展性，为后续接入移动端、Telegram Bot 交互、多用户支持打下基础。
