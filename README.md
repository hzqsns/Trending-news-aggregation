# 📊 投研 Agent — 智能新闻聚合系统

自动采集全球财经/加密货币新闻 → AI 分析研判 → Web 展示 → 多渠道推送

参考 [@xingpt 的 Agent 化投研系统理念](https://x.com/xingpt/status/2025219080421277813)设计。

## 系统架构

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ 数据采集      │ ──→ │ AI 分析引擎   │ ──→ │ Web 前端展示  │     │ 多渠道推送    │
│ RSS/API/爬虫 │     │ 评分/情绪/预警 │     │ React SPA   │     │ TG/微信/QQ   │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                          ↕                      ↕
                    ┌──────────────┐     ┌──────────────┐
                    │ SQLite 数据库  │     │ FastAPI 后端  │
                    └──────────────┘     └──────────────┘
```

## 快速开始

### 前提条件

- Python >= 3.10
- Node.js >= 20
- pnpm

### 1. 启动后端

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate   # macOS/Linux
# venv\Scripts\activate    # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（可选，有默认值）
cp .env.example .env
# 编辑 .env 填入 AI API Key 等配置

# 启动
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

首次启动会自动：
- 创建 SQLite 数据库
- 创建默认管理员账号 `admin / admin123`
- 启动定时采集调度器

### 2. 启动前端

```bash
cd frontend

# 安装依赖
pnpm install

# 开发模式
pnpm dev
```

打开浏览器访问 http://localhost:5173 ，用 `admin / admin123` 登录。

## 登录后首先要做的事

1. **修改密码** — 系统设置中修改默认密码
2. **配置 AI** — 在「系统设置 → AI 配置」中填入你的 API Key（支持 OpenAI / DeepSeek 等兼容接口）
3. **配置推送**（可选）— 在「系统设置 → 推送渠道」中配置 Telegram / 微信 / QQ 推送
4. **查看 Skills** — 在「Skills」页面查看和管理 AI 决策框架

## 功能模块

| 模块 | 说明 |
|------|------|
| **Dashboard** | 数据概览：今日新闻数、活跃预警、市场情绪、热门新闻 Top10 |
| **新闻流** | 实时新闻时间线，支持分类/搜索/重要度筛选 |
| **AI 日报** | 每日 07:30 / 22:00 自动生成市场摘要（需配置 AI） |
| **预警中心** | 高重要度事件自动触发预警信号 |
| **Skills** | 查看/管理 AI 决策框架（评分器/监控器/生成器） |
| **系统设置** | Web 可视化配置所有参数（数据源/AI/推送/调度策略） |

## 数据源

| 数据源 | 类型 | 分类 |
|--------|------|------|
| 新浪财经 | RSS | A 股 |
| 华尔街见闻 | RSS | 全球 |
| 36 氪 | RSS | 科技 |
| CoinDesk | RSS | 加密货币 |
| Reuters | RSS | 全球 |
| CoinGecko | API | 加密货币 |

可在「系统设置 → 数据源配置」中启用/禁用，也可通过代码扩展新数据源。

## 推送渠道

| 渠道 | 服务 | 配置位置 |
|------|------|----------|
| Telegram | Bot API | 系统设置 → 推送渠道 |
| 微信 | PushPlus | 系统设置 → 推送渠道 |
| QQ | Qmsg 酱 | 系统设置 → 推送渠道 |

## 技术栈

| 层次 | 技术 |
|------|------|
| 后端 | Python 3.10 + FastAPI + SQLAlchemy + APScheduler |
| 前端 | React 19 + Vite + TailwindCSS 4 + Zustand |
| 数据库 | SQLite（可迁移 PostgreSQL） |
| 认证 | JWT (python-jose + bcrypt) |
| AI | OpenAI 兼容接口（GPT-4o / DeepSeek） |

## 项目结构

```
├── backend/                  # Python 后端
│   ├── app/
│   │   ├── main.py           # FastAPI 入口
│   │   ├── config.py         # 配置管理
│   │   ├── auth.py           # JWT 认证
│   │   ├── database.py       # 数据库
│   │   ├── scheduler.py      # 定时调度
│   │   ├── models/           # 数据模型（6 个表）
│   │   ├── api/              # API 路由（7 个模块）
│   │   ├── sources/          # 数据采集插件
│   │   ├── skills/           # AI 决策引擎
│   │   ├── ai/               # LLM 客户端
│   │   └── notifiers/        # 推送通知
│   ├── requirements.txt
│   └── .env.example
├── frontend/                 # React 前端
│   ├── src/
│   │   ├── pages/            # 6 个页面
│   │   ├── components/       # 布局组件
│   │   ├── api/              # API 调用层
│   │   └── stores/           # 状态管理
│   └── package.json
├── docs/
│   └── TECHNICAL_DESIGN.md   # 技术设计文档
└── README.md
```
