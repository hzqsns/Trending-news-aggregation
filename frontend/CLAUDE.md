[根目录](../CLAUDE.md) > **frontend**

# frontend — React TypeScript SPA 模块

## 变更记录 (Changelog)

| 日期 | 版本 | 变更说明 |
|---|---|---|
| 2026-03-23 | v2.1 | 初始文档生成；记录 Bookmarks、TwitterTracking 页面，useNewsSocket hook，bookmarksApi 模块 |

---

## 模块职责

基于 React 19 + Vite 7 的单页应用。提供投研 Agent 的 Web 控制台：新闻浏览、书签管理、AI 日报阅读、预警查看、Skill 配置、Twitter 追踪管理、系统设置。通过 Axios 与后端 REST API 通信，通过 WebSocket 接收实时推送。

---

## 入口与启动

| 文件 | 说明 |
|---|---|
| `index.html` | HTML 入口，挂载 `#root` |
| `src/main.tsx` | React 渲染入口，`createRoot` + 全局主题初始化 |
| `src/App.tsx` | 路由配置（BrowserRouter），`ProtectedRoute` 守卫（检查 Zustand token） |
| `src/components/Layout.tsx` | 主布局：侧边栏导航（桌面）+ 顶部 Header（移动端）+ `<Outlet>` |
| `vite.config.ts` | Vite 配置，`@vitejs/plugin-react`，`@tailwindcss/vite`，`@` 路径别名 |

开发命令：

```bash
cd frontend
pnpm install
pnpm dev      # 开发服务器 http://localhost:5173
pnpm build    # TypeScript 编译 + Vite 构建 → dist/
pnpm lint     # ESLint（typescript-eslint + react-hooks + react-refresh）
pnpm preview  # 预览生产构建
```

---

## 路由结构

所有页面（除 `/login`）均被 `ProtectedRoute` 保护，未登录自动重定向到 `/login`。

| 路径 | 组件 | 说明 |
|---|---|---|
| `/login` | `Login` | 登录页，调用 `POST /api/auth/login`，成功后存 Zustand + 跳转 `/` |
| `/` | `Dashboard` | 概览仪表盘，统计数据 + 情绪历史图表（Recharts） |
| `/news` | `NewsFeed` | 新闻流，支持分类/来源/重要度/搜索过滤，实时 WebSocket 刷新 |
| `/bookmarks` | `Bookmarks` | 收藏夹，标签过滤 + 搜索，内联编辑备注/标签 |
| `/reports` | `Reports` | AI 日报列表 + Markdown 渲染（react-markdown + remark-gfm） |
| `/alerts` | `Alerts` | 预警中心，active/resolved 分组，一键 resolve |
| `/skills` | `Skills` | Skill 管理，查看/编辑/创建 AI Skill 配置 |
| `/twitter` | `TwitterTracking` | Twitter 追踪：博主列表管理、手动采集、Cookie 导入、Auth 测试 |
| `/settings` | `Settings` | 系统设置，分类展示，批量保存，AI 连接测试 |

---

## 对外接口（API 模块）

`src/api/client.ts`：Axios 实例，`baseURL=/api`，`timeout=120s`；请求拦截注入 JWT；响应拦截处理 401。

`src/api/index.ts`：8 个具名 API 模块：

| 模块 | 覆盖端点前缀 |
|---|---|
| `dashboardApi` | `/dashboard` |
| `articlesApi` | `/articles` |
| `reportsApi` | `/reports` |
| `alertsApi` | `/alerts` |
| `skillsApi` | `/skills` |
| `settingsApi` | `/settings`（含 ai-providers、test-ai） |
| `twitterApi` | `/twitter` |
| `bookmarksApi` | `/bookmarks`（含 tags、status 批量查询）|

---

## 关键依赖

| 包 | 版本 | 用途 |
|---|---|---|
| `react` | 19.2 | UI 框架 |
| `react-dom` | 19.2 | DOM 渲染 |
| `react-router-dom` | 7.13 | SPA 路由 |
| `zustand` | 5.0 | 轻量状态管理 |
| `axios` | 1.13 | HTTP 客户端 |
| `recharts` | 3.7 | 图表（Dashboard 情绪历史） |
| `react-markdown` | 10.1 | Markdown 渲染（AI 日报） |
| `remark-gfm` | 4.0 | GFM 扩展（表格、删除线等） |
| `lucide-react` | 0.575 | 图标库 |
| `date-fns` | 4.1 | 日期格式化 |
| `clsx` + `tailwind-merge` | — | 条件类名合并 |
| `tailwindcss` | 4.2 | CSS 框架（via `@tailwindcss/vite`） |
| `vite` | 7.3 | 构建工具 |
| `typescript` | 5.9 | 类型系统 |

---

## 数据模型（前端类型）

核心接口定义分散于各页面组件（尚无独立 `types/` 目录），主要：

```typescript
// stores/auth.ts
interface UserInfo { id: number; username: string }
interface AuthState { token: string; user: UserInfo | null; ... }

// api/index.ts (隐式)
// Article: { id, title, url, source, category, importance, sentiment, ai_analysis, tags[], published_at, fetched_at }
// Bookmark: { id, article_id, user_id, note, tags[], created_at, updated_at, article: Article }
```

---

## 状态管理

| Store | 文件 | 持久化 | 说明 |
|---|---|---|---|
| `useAuthStore` | `stores/auth.ts` | localStorage (`news-agent-auth`) | token、user、setAuth、logout、isAuthenticated |
| `useThemeStore` | `stores/theme.ts` | localStorage | theme: `light` / `dark` / `system`，自动同步 `document.documentElement.className` |

---

## WebSocket Hook

`src/hooks/useNewsSocket.ts`：

```typescript
useNewsSocket({
  new_article: (data) => { /* 追加到列表 */ },
  new_alert: (data) => { /* 显示 toast */ },
})
```

自动重连（断线后 5s 重试），使用 `wss://` 或 `ws://` 取决于页面协议。

---

## 测试与质量

- 当前无测试文件（无 `*.test.ts` / `*.spec.ts`）
- ESLint 配置：`eslint.config.js`，规则：`typescript-eslint` + `react-hooks` + `react-refresh`
- 建议添加：Vitest + React Testing Library，优先覆盖 `stores/auth.ts`（persist 逻辑）和 `api/index.ts`（参数构造）

---

## 常见问题 (FAQ)

**Q: 前端如何代理 API 请求？**
A: Vite 开发模式下通过 `vite.config.ts` 中的 `proxy` 配置将 `/api` 代理到 `http://127.0.0.1:8000`。生产部署需用 Nginx 配置同样的代理。

**Q: 如何新增一个侧边栏导航项？**
A: 在 `src/components/Layout.tsx` 的 `navItems` 数组追加 `{ to: '/path', icon: IconComponent, label: '标签' }`。

**Q: 主题颜色如何自定义？**
A: 通过 TailwindCSS 4 的 CSS 变量主题，在 `src/index.css` 中修改 `--color-sidebar`、`--color-primary` 等 CSS 变量。

**Q: Markdown 日报不渲染表格？**
A: 需要同时引入 `remark-gfm` 插件，`Reports.tsx` 中已配置，检查 `<ReactMarkdown remarkPlugins={[remarkGfm]}>` 是否存在。

---

## 相关文件清单

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── eslint.config.js
├── vite.config.ts (如存在) 或 通过 package.json 配置
└── src/
    ├── main.tsx              # React 入口
    ├── App.tsx               # 路由配置，ProtectedRoute
    ├── api/
    │   ├── client.ts         # Axios 实例，JWT 拦截，401 处理
    │   └── index.ts          # 8 个 API 模块
    ├── stores/
    │   ├── auth.ts           # JWT 持久化 store
    │   └── theme.ts          # 主题 store
    ├── hooks/
    │   └── useNewsSocket.ts  # WebSocket 自动重连 hook
    ├── components/
    │   └── Layout.tsx        # 主布局，侧边栏，移动端 Header
    ├── pages/
    │   ├── Login.tsx
    │   ├── Dashboard.tsx
    │   ├── NewsFeed.tsx
    │   ├── Bookmarks.tsx
    │   ├── Reports.tsx
    │   ├── Alerts.tsx
    │   ├── Skills.tsx
    │   ├── TwitterTracking.tsx
    │   └── Settings.tsx
    └── lib/
        └── utils.ts          # clsx + tailwind-merge 工具函数
```
