# 多 Agent 平台重构 — 回退清单

每个 Phase 回退前先执行 `cd backend && python tests/baseline.py`，保留当前快照备用。

---

## Phase 1 — 平台骨架回退

**触发条件**：lifespan 启动失败 / import 循环 / SQLite PRAGMA 报错

**步骤**：
1. 恢复 `main.py` — 删除 `register_investment_agent` 调用，恢复内联 `BUILTIN_SKILLS`
2. 恢复 `database.py` — 移除 `@event.listens_for` 块
3. 重启后端，验证 `GET /health` 返回 200

**验证**：`/health` 正常、Swagger `/docs` 可访问、定时任务日志无异常

---

## Phase 2 — DB 迁移 + 前端共享 UI 回退

**触发条件**：`agent_key` 列导致查询报错 / 通知重复推送 / 前端页面加载失败

**步骤**：
1. 停止服务，备份 `backend/data/news_agent.db`
2. SQLite 不支持 DROP COLUMN，需用 DB Browser 或脚本重建旧表结构
3. 前端恢复单 Agent 导航，删除 AgentSwitcher 组件引用

**验证**：`/api/articles`、`/api/reports`、`/api/settings` 响应正常；无重复推送日志

---

## Phase 3 — 爬虫层 + 前端 Agent 架构回退

**触发条件**：crawlers/ 重构导致现有数据源采集失败 / 路由命名空间冲突

**步骤**：
1. 恢复 `sources/` 目录引用（manager.py ALL_SOURCES 指向旧 sources）
2. 前端 App.tsx 移除 `/invest/*` `/tech/*` 命名空间，恢复旧路由
3. Layout.tsx 恢复硬编码 navItems

**验证**：新闻采集正常、所有旧路由可访问

---

## Phase 4 — Tech Info Agent 回退

**触发条件**：tech_info agent 影响投研 agent 稳定性

**步骤**：
1. 从 AgentRegistry 取消注册 tech_info agent（注释掉 register call）
2. 从 main.py 移除 tech_info router
3. 前端删除 `/tech/*` 路由及导航入口

**验证**：投研 Agent 所有功能恢复正常

---

## 通用操作

- **备份数据库**：`cp backend/data/news_agent.db backend/data/news_agent.db.bak`
- **快照对比**：`python backend/tests/baseline.py` 后对比 `baseline_snapshot.json`
- **回退 git**：`git revert <commit>` 或 `git stash`（Phase 1 纯包装，revert 最安全）
