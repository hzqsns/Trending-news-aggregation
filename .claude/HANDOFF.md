# Agent Handoff Context
> 当 Claude 触发 rate limit 时，其他 agent 工具可读取本文件接续工作。
> 每次会话结束或切换时更新此文件。

---

## 📅 最后更新
- **时间**：2026-04-05
- **模型**：Claude Sonnet 4.6（主力）/ Opus 4.6（用于架构分析）
- **仓库**：`hzqsns/Trending-news-aggregation`（master 分支，已推送）

---

## 🏗 项目概况

**项目**：投研 Agent — AI 驱动的金融新闻聚合与投研系统

**技术栈**：
- 后端：Python 3.11 + FastAPI 0.115 + SQLite (aiosqlite) + APScheduler
- 前端：React 19 + Vite 7 + TypeScript + TailwindCSS 4 + Zustand
- AI：双格式 LLM 客户端（OpenAI + Anthropic），6 服务商预设
- 启动：`./start.sh`（后端 :8000 + 前端 :5173）

**当前版本**：V2.1（已实现）

---

## ✅ 本次会话已完成的工作

| Commit | 内容 |
|--------|------|
| `aba6fed` | V2.1：宏观指标（FRED API）+ 历史事件库 |
| `7942c2c` | 修复宏观 DELETE+INSERT、自动种子历史事件、增加国际 RSS 源 |
| `fd5d31d` | 宏观 AI 分析面板 + 扩展/自定义时间范围 |
| `b1d580e` | 修复 AI 分析 JSON fence 解析 + 改进错误提示 |
| `3b3cc8e` | OpenAlice sidecar 集成（status/ask/market proxy）|
| `08f7049` | auto commit（hooks 测试产生）|

**已推送到远程** ✅

---

## 🔧 本次会话新增的全局配置

### Auto Commit Hook（全局生效）
- **配置文件**：`~/.claude/settings.json`
- **Hook 类型**：`PostToolUse` on `Write|Edit`
- **逻辑**：prompt hook（LLM 语义判断是否构成完整功能点）→ command hook（执行 commit+push）
- **脚本**：`~/.claude/hooks/auto-commit-push.sh`
- **阈值**：语义判断，至少 3 文件或 30+ 行才考虑触发

---

## 📋 当前最重要的待完成任务

### 下一个大目标：多 Agent 平台架构重构

**计划文件**：`.claude/plan/multi-agent-platform.md`（v2 修订版）

**目标**：将当前投研 Agent 改造为可扩展的多 Agent 平台，新增"技术信息 Agent"。

**执行命令**（在新会话中运行）：
```
/ccg:execute .claude/plan/multi-agent-platform.md
```

---

## 📐 架构决策摘要（重要，接手时必读）

### 核心决策（不可更改）

1. **不用微前端** — lazy route groups 足够，Module Federation 对小团队过重
2. **模块化单体** — 保持单一 FastAPI 进程，不拆微服务
3. **DB 加列方案** — 现有表加 `agent_key` 列，不建 content_items/agent_content 双表
4. **静态 AgentRegistry** — 显式 Python 代码注册，不做插件发现/manifest DSL
5. **无 EventBus** — 通知继续直接调用，等 Agent > 5 再考虑
6. **无 AgentLauncher** — 默认跳转 last-used Agent（localStorage 持久化）

### 后端目标目录结构（关键）
```
backend/app/
├── platform/          # registry.py, manifest.py, scheduler.py, config.py
├── crawlers/          # 原 sources/ 重构（扁平，含 github/v2ex/linux_do/hackernews）
├── agents/
│   ├── investment/    # 薄 wrapper，委托现有代码
│   └── tech_info/     # 新 Agent
├── ai/                # 不变
├── notifiers/         # 不变
└── models/            # 加 agent_key 列
```

### 前端目标结构（关键）
```
frontend/src/
├── config/agents.ts   # AgentManifest 定义
├── stores/agent.ts    # last-used Agent 持久化
├── components/
│   ├── AgentSwitcher.tsx  # 桌面: 侧边栏顶部下拉; 移动: 底部 Tab Bar
│   └── ui/            # 共享组件（必须在写 Tech 页面之前提取）
└── pages/
    ├── invest/        # 现有 13 页迁移到这里
    ├── tech/          # 6 个新页面
    └── shared/        # Login, Settings
```

---

## 📍 实施顺序（5 Phase）

```
Phase 0: 回归基线（收集 fetch/score/push 指标，定义 rollback 规则）
Phase 1: 平台骨架（WAL模式 + AgentRegistry + InvestmentAgent 薄wrapper + main.py集成）
Phase 2: DB隔离 + 前端共享UI（加agent_key列 + 提取components/ui/）
Phase 3: 共享爬虫层 + 前端Agent架构（sources→crawlers + 4新爬虫 + 路由命名空间）
Phase 4: Tech Info Agent（后端skills/jobs/routes + 前端6页面）
```

---

## ⚠️ 注意事项（接手时必看）

1. **Phase 1 wrapper 不能引入 scoped config** — 纯薄包装，零行为变更，否则回归测试无法通过
2. **Phase 2 DB 迁移前必须备份 `.db` 文件** — SQLite ALTER TABLE 不支持 DROP COLUMN
3. **通知双跑策略** — DB 迁移期间 notifier 同时查旧路径和新路径，避免遗漏
4. **UI 组件必须前置** — 不允许在 `components/ui/` 建立之前写任何 Tech Agent 页面
5. **移动端不用 Discord 侧边栏** — 移动端 < 768px 用底部 Tab Bar 切换 Agent
6. **Postgres 退出触发条件** — 出现 "database is locked" / Agent > 5 / 多进程时切换

---

## 🔑 关键文件路径

| 文件 | 说明 |
|------|------|
| `.claude/plan/multi-agent-platform.md` | 完整实施计划（v2 修订版） |
| `backend/app/sources/base.py` | NewsSource ABC（即将重构为 CrawlerPlugin） |
| `backend/app/sources/manager.py` | fetch_all_sources()（即将重构） |
| `backend/app/skills/engine.py` | AI 技能引擎（投研 Agent 将 import 此文件） |
| `backend/app/notifiers/manager.py` | 推送管理器（不变） |
| `backend/app/scheduler.py` | APScheduler 9 个任务（即将迁移到 SchedulerKernel） |
| `backend/app/main.py` | lifespan 入口（Phase 1 修改此文件） |
| `frontend/src/components/Layout.tsx` | 硬编码 navItems（Phase 3 重构） |
| `frontend/src/App.tsx` | 路由定义（Phase 3 加命名空间） |
| `~/.claude/settings.json` | 全局 Claude 配置（含 auto commit hook） |
| `~/.claude/hooks/auto-commit-push.sh` | 自动提交脚本 |

---

## 💬 上下文关键词（用于语义搜索）

多Agent平台、AgentRegistry、CrawlerPlugin、agent_key、Tech Info Agent、GitHub Trending、V2EX、Linux.do、HackerNews、投研Agent、模块化单体、Workspace切换、WAL模式
