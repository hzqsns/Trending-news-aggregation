# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

投研 Agent — AI-powered financial news aggregation and investment research system. Full-stack SPA with Python FastAPI backend and React TypeScript frontend. Collects news from 14+ sources, scores importance via LLM, generates daily reports, and pushes alerts through Telegram/WeChat/QQ.

## Commands

### Startup / Shutdown
```bash
./start.sh   # Creates venv, installs deps, starts backend + frontend
./stop.sh    # Stops all services
```

### Backend (manual)
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Frontend
```bash
cd frontend
pnpm install
pnpm dev      # Dev server on http://localhost:5173
pnpm build    # Production build to dist/
pnpm lint     # ESLint
```

### Access Points
- Frontend: http://localhost:5173
- Backend API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs
- Default login: admin / admin123

## Architecture

```
Frontend (React SPA)  ──REST/WebSocket──>  Backend (FastAPI)
                                              │
                                    ┌─────────┼─────────┐
                                    │         │         │
                               Sources    Skills    Notifiers
                             (RSS/API)   (LLM AI)  (TG/WeChat/QQ)
                                    │         │         │
                                    └────> SQLite <─────┘
```

### Three-tier Agent Architecture
1. **Knowledge Base** (Sources): Data collection from RSS feeds, NewsAPI, CoinGecko
2. **Skills** (AI Engine): LLM-powered scoring, sentiment analysis, report generation
3. **CRON** (Scheduler): Automated orchestration — fetch every 15min, score, detect anomalies, generate reports at 07:30/22:00, push notifications

### Data Flow
News sources → `sources/manager.py` fetch → DB → `skills/engine.py` AI scoring → `notifiers/manager.py` push → Telegram/WeChat/QQ

### Auth Flow
POST `/api/auth/login` → JWT token → Zustand auth store → Axios interceptor adds Bearer header → 401 triggers auto-logout

### WebSocket
`ws://localhost:8000/api/ws` — backend broadcasts new articles and alerts in real-time to connected frontends.

## Backend Structure (`backend/app/`)

| Directory/File | Purpose |
|---|---|
| `main.py` | FastAPI app, lifespan (init DB, default user, built-in skills, scheduler) |
| `config.py` | Pydantic Settings from `.env` |
| `database.py` | SQLAlchemy async engine (SQLite + aiosqlite) |
| `scheduler.py` | APScheduler cron job definitions (7 jobs) |
| `auth.py` | JWT token creation/validation |
| `models/` | 7 SQLAlchemy ORM models (articles, alerts, reports, skills, sentiments, settings, users) |
| `api/` | FastAPI routers: auth, articles, dashboard, reports, alerts, skills, settings, ws |
| `sources/` | Data plugins: `base.py` interface → `rss.py`, `crypto.py`, `newsapi.py`, `manager.py` |
| `skills/` | `engine.py` — assembles LLM prompts from skill configs, parses structured JSON output |
| `ai/` | `client.py` — OpenAI-compatible LLM client (works with GPT, DeepSeek, Ollama, etc.) |
| `notifiers/` | `base.py` interface → `telegram.py`, `wechat.py`, `qq.py`, `manager.py` |

## Frontend Structure (`frontend/src/`)

| Directory/File | Purpose |
|---|---|
| `pages/` | Dashboard, NewsFeed, Reports, Alerts, Skills, Settings, Login |
| `stores/` | Zustand stores (auth with JWT, theme with dark mode) |
| `api/client.ts` | Axios instance with JWT interceptor |
| `components/Layout.tsx` | Main layout with sidebar navigation |

## Database

SQLite at `backend/data/news_agent.db`, auto-created on first startup with all tables and default data. 7 tables: users, articles, alerts, daily_reports, skills, sentiment_snapshots, system_settings.

Uses SQLAlchemy 2.0 async style with `Mapped[]` typed columns and a custom `JSONField` for SQLite JSON compatibility.

## Key Conventions

- **Async everywhere**: All backend I/O is async (SQLAlchemy, httpx, APScheduler)
- **Plugin pattern**: Sources and Notifiers inherit from base class with standard interface (`fetch()` / `send()`)
- **Skills as config**: AI skills stored as JSONB in DB, interpreted by LLM at runtime via prompt assembly
- **LLM client**: OpenAI-compatible API; configurable via `AI_API_KEY`, `AI_API_BASE`, `AI_MODEL` env vars
- **Frontend state**: Zustand (not Redux), functional components with hooks
- **Styling**: TailwindCSS 4 with `@tailwindcss/vite` plugin
- **Charts**: Recharts library
- **Markdown rendering**: react-markdown + remark-gfm for AI reports

## Adding New Components

**New data source**: Create `sources/my_source.py` inheriting `NewsSource`, implement `fetch() → list[NewsItem]`, register in `manager.py`

**New push channel**: Create `notifiers/my_notifier.py` inheriting `Notifier`, implement `send()`, add config check in `manager.py`

**New API endpoint**: Create route file in `api/`, define FastAPI Router, include in `api/router.py`

**New frontend page**: Create component in `pages/`, add route in App.tsx, add sidebar link in Layout.tsx

## Environment Variables

Key vars in `backend/.env` (see `.env.example`):
- `JWT_SECRET` — required for auth
- `AI_API_KEY`, `AI_API_BASE`, `AI_MODEL` — LLM configuration
- `DATABASE_URL` — default: `sqlite+aiosqlite:///./data/news_agent.db`
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — Telegram push
- `PUSHPLUS_TOKEN` — WeChat push
- `QMSG_KEY` — QQ push
- `FRONTEND_URL` — CORS origin (default: `http://localhost:5173`)

## Roadmap (Not Yet Implemented)

- **V2.1**: Macro indicator tracking, financial calendar, bookmarks/notes, historical event library
- **V2.2**: Structured skill definition UI, skill backtesting
- **V2.3**: Vector semantic search, historical pattern matching, portfolio tracking, multi-signal fusion alerts
- **V2.4**: Content production agent, AI writing pipeline, multi-platform publishing
