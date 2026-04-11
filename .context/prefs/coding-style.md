# Coding Style Guide

> 此文件定义团队编码规范，所有 LLM 工具在修改代码时必须遵守。
> 提交到 Git，团队共享。

## General
- Prefer small, reviewable changes; avoid unrelated refactors.
- Keep functions short (<50 lines); avoid deep nesting (≤3 levels).
- Name things explicitly; no single-letter variables except loop counters.
- Handle errors explicitly; never swallow errors silently.

## Backend (Python)
- All I/O (DB, HTTP) must use async/await.
- SQLAlchemy 2.0 style: `Mapped[]` typed columns, `async with async_session()`.
- Use `JSONField` (custom TypeDecorator) for JSON columns in SQLite.
- Plugin pattern: Sources extend `NewsSource`, Notifiers extend `Notifier`.

## Frontend (TypeScript/React)
- Functional components + hooks only (no class components).
- State management via Zustand (not Redux).
- TailwindCSS 4 CSS variable tokens: `bg-card`, `bg-primary`, `text-text`, `border-border`.
- Charts: Recharts with CSS variable colors (`var(--color-border)` etc).
- Path alias: `@/` maps to `src/`.

## Git Commits
- Conventional Commits, imperative mood.
- Atomic commits: one logical change per commit.

## Testing
- No automated tests currently; manual verification via backend API + frontend UI.
- When adding tests: pytest + pytest-asyncio (backend), Vitest + RTL (frontend).

## Security
- Never log secrets (tokens/keys/cookies/JWT).
- Validate inputs at trust boundaries (API layer).
- JWT: HS256, 7-day expiry, auto-logout on 401.
