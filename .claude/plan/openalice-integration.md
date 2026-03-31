# 实施计划：OpenAlice 集成

## 调研结论

### OpenAlice 是什么
- **文件驱动的 AI 交易引擎**（TypeScript/Hono），非插件/库
- 功能：多交易所下单（CCXT 100+ 加密交易所、Alpaca 美股、IBKR 全品类）、OpenBB 全品类行情、技术分析、AI 认知/记忆、Trading-as-Git 工作流
- 许可证：**AGPL-3.0**（网络交互的衍生作品必须开源）

### 直接集成可行性分析

| 方式 | 可行性 | 说明 |
|------|--------|------|
| 作为 npm 包导入 | ❌ 不可行 | 它不是库，是完整应用 |
| iframe 嵌入其 Web UI | ⚠️ 部分可行 | UI 在 :3002，可以 iframe 但体验割裂 |
| 共享数据库 | ❌ 不可行 | 它用文件系统（JSON/JSONL），我们用 SQLite |
| **Sidecar + API 代理** | ✅ 推荐 | 作为伴侣服务运行，通过 HTTP/MCP 通信 |
| 复制其代码 | ❌ AGPL 风险 | 衍生作品必须同样 AGPL 开源 |

### 推荐方案：Sidecar 集成（3 个接触点）

```
┌─────────────────────────────────────┐
│  投研 Agent (Python/FastAPI :8000)  │
│  ┌───────────┐  ┌────────────────┐  │
│  │  /api/     │  │ Proxy Module   │──┼──→ OpenAlice :3002 (MCP Ask)
│  │  现有路由  │  │ /api/alice/*   │──┼──→ OpenAlice :3002 (OpenBB HTTP)
│  └───────────┘  └────────────────┘  │
└──────────────────┬──────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │  Frontend (React :5173)     │
    │  ┌──────────┐ ┌──────────┐  │
    │  │ 现有页面  │ │ Alice    │  │
    │  │          │ │ 集成页面  │  │
    │  └──────────┘ └──────────┘  │
    └─────────────────────────────┘
```

**接触点 1 — MCP Ask（AI 对话）**：后端通过 HTTP 调用 OpenAlice 的 MCP Ask 端点，获取 AI 交易分析
**接触点 2 — OpenBB HTTP（行情数据）**：后端代理 OpenAlice 内嵌的 OpenBB 服务器，获取股票/加密/宏观数据
**接触点 3 — Web UI 链接**：前端新增导航入口，跳转或 iframe 嵌入 OpenAlice 的完整交易界面

---

## 任务类型
- [x] 前端 (→ Gemini)
- [x] 后端 (→ Codex)
- [x] 全栈 (→ 并行)

## 前置条件

- 用户已安装 Node.js 22+ 和 pnpm 10+
- 用户已克隆 OpenAlice 仓库并完成 `pnpm install && pnpm build`
- OpenAlice 已配置 `connectors.json` 启用 MCP Ask
- OpenAlice 已配置 `market-data.json` 启用 embedded OpenBB HTTP server

## 实施步骤

### Phase 1：后端 — OpenAlice 连接层（3 文件）

#### Step 1.1 新增系统设置项
**文件**: `backend/app/models/setting.py` (修改)

在 `DEFAULT_SETTINGS` 中新增：
```python
{"key": "openalice_enabled", "value": "false", "category": "openalice", "label": "启用 OpenAlice", "field_type": "boolean"},
{"key": "openalice_base_url", "value": "http://localhost:3002", "category": "openalice", "label": "OpenAlice 地址", "field_type": "text"},
```

#### Step 1.2 新增 OpenAlice 代理路由
**文件**: `backend/app/api/alice.py` (新建)

```python
# 3 个端点:
# GET  /api/alice/status     → 检测 OpenAlice 是否在线 (ping :3002/health 或 /)
# POST /api/alice/ask        → 代理 MCP Ask 对话请求
# GET  /api/alice/market/*   → 代理 OpenBB HTTP API (股票/加密/宏观数据)

router = APIRouter()

async def _get_alice_config(session) -> dict:
    """从 system_settings 读取 openalice_enabled + openalice_base_url"""

@router.get("/status")
async def alice_status(session):
    """HTTP GET openalice_base_url, 返回 {online: bool, version: str}"""

@router.post("/ask")
async def alice_ask(payload: AskPayload, session):
    """代理 MCP Ask: POST openalice_base_url/mcp/ask, 返回 AI 分析结果"""

@router.get("/market/{path:path}")
async def alice_market_proxy(path: str, request: Request, session):
    """透传 GET openalice_base_url/api/{path}, 代理 OpenBB 行情数据"""
```

#### Step 1.3 注册路由
**文件**: `backend/app/api/router.py` (修改)

```python
from app.api import alice
api_router.include_router(alice.router, prefix="/alice", tags=["OpenAlice"])
```

### Phase 2：前端 — OpenAlice 集成页面（3 文件）

#### Step 2.1 新增 API 模块
**文件**: `frontend/src/api/index.ts` (修改)

```typescript
export const aliceApi = {
  status: () => client.get('/alice/status'),
  ask: (message: string) => client.post('/alice/ask', { message }),
  market: (path: string) => client.get(`/alice/market/${path}`),
}
```

#### Step 2.2 新增 OpenAlice 集成页面
**文件**: `frontend/src/pages/OpenAlice.tsx` (新建)

页面包含 3 个区域：
1. **连接状态** — 显示 OpenAlice 是否在线，版本号，一键跳转完整 UI
2. **AI 交易助手** — 聊天输入框，通过 MCP Ask 与 Alice 对话，获取交易分析/建议
3. **实时行情** — 从 OpenBB 代理拉取 Top 加密/美股行情卡片

```
┌─ OpenAlice 集成 ──────────────────────────────────┐
│ [● 已连接 v0.x.x]           [打开完整界面 →]      │
├───────────────────────────────────────────────────┤
│                                                   │
│  ┌─ AI 交易助手 ─────────────────────────────┐    │
│  │ [Alice]: 当前 BTC 处于 $67,500，4h RSI    │    │
│  │ 超买区域，建议观望或轻仓做空...             │    │
│  │                                           │    │
│  │ [输入消息...                    ] [发送]    │    │
│  └───────────────────────────────────────────┘    │
│                                                   │
│  ┌─ 实时行情看板 ────────────────────────────┐    │
│  │ BTC $67,500 +2.3%  │ ETH $3,450 -0.5%    │    │
│  │ SPY $515.30 +0.8%  │ QQQ $440.20 +1.2%   │    │
│  └───────────────────────────────────────────┘    │
└───────────────────────────────────────────────────┘
```

#### Step 2.3 路由 + 导航
**文件**: `frontend/src/App.tsx` (修改) — 添加 `/alice` 路由
**文件**: `frontend/src/components/Layout.tsx` (修改) — 添加 Bot 图标 "OpenAlice" 导航项

### Phase 3：启动脚本集成（1 文件）

#### Step 3.1 修改 start.sh
**文件**: `start.sh` (修改)

```bash
# 检测 OpenAlice 目录是否存在，如存在则自动启动
ALICE_DIR="../OpenAlice"  # 或从 .env 读取
if [ -d "$ALICE_DIR" ] && command -v node &>/dev/null; then
    echo "▶ 启动 OpenAlice..."
    cd "$ALICE_DIR" && pnpm start &
    ALICE_PID=$!
    echo "$ALICE_PID" >> .pids
fi
```

---

## 关键文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `backend/app/models/setting.py` | 修改 | 新增 2 个 openalice_ 设置项 |
| `backend/app/api/alice.py` | 新建 | 3 个代理端点 (status/ask/market) |
| `backend/app/api/router.py` | 修改 | 注册 alice router |
| `frontend/src/api/index.ts` | 修改 | 新增 aliceApi 模块 |
| `frontend/src/pages/OpenAlice.tsx` | 新建 | 集成页面 (连接状态+AI聊天+行情) |
| `frontend/src/App.tsx` | 修改 | 添加 /alice 路由 |
| `frontend/src/components/Layout.tsx` | 修改 | 添加导航项 |
| `start.sh` | 修改 | 可选：自动启动 OpenAlice |

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| OpenAlice 未运行时页面报错 | `GET /alice/status` 先检测，未连接时显示安装引导 |
| AGPL-3.0 传染性 | 仅通过 HTTP 代理通信，不复制/修改 OpenAlice 源码，保持进程隔离 |
| MCP Ask 端点格式不稳定 | 后端做 try/except + 格式兼容层 |
| Node.js 22 不一定安装 | 设为可选功能（openalice_enabled=false 默认关闭） |
| OpenBB API 格式变化 | 后端 market proxy 透传，不做深度解析 |

## 可选增强（后续迭代）

- **P1**: 将 OpenAlice 的交易信号注入我们的 Alert 系统
- **P2**: 从 OpenAlice 的 OpenBB 数据替换我们的 FRED 宏观数据源（更全面）
- **P3**: 将我们的新闻评分结果通过 MCP 回传给 OpenAlice 作为交易决策输入

## SESSION_ID（供 /ccg:execute 使用）
- CODEX_SESSION: N/A（本次规划未调用外部模型）
- GEMINI_SESSION: N/A
