# Proposal: 宏观指标追踪 + 历史事件库

**Change ID**: macro-indicators-historical-events
**Status**: proposed
**Date**: 2026-03-25

---

## Overview

Implement two new V2.1 features:
1. **Macro Indicators Tracking** — fetch 5 FRED series (M2SL, FEDFUNDS, CPIAUCSL, DGS10, UNRATE) via free CSV API, store in SQLite, display as indicator cards + collapsible line charts with 3M/6M/1Y/3Y front-end time range filtering
2. **Historical Events Library** — CRUD for significant financial events, 5 categories, 10 builtin seeded events (immutable), expandable cards with key metrics editor

---

## Discovered Constraints

### Hard Constraints (must not violate)

**Backend**:
- All DB operations via `async with async_session() as session:` (SQLAlchemy 2.0 async)
- Models must use `Mapped[]` / `mapped_column()` annotations and inherit from `app.database.Base`
- New models **must be imported in `app/main.py`** to trigger `Base.metadata.create_all`
- `JSONField` (custom TypeDecorator in `database.py`) required for JSON columns in SQLite
- API routers must be registered in `app/api/router.py` via `include_router`
- All protected endpoints must use `Depends(get_current_user)` and `Depends(get_session)`
- FRED CSV endpoint is **free, no API key required**: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES_ID>`
- Missing values in FRED CSV are represented as `"."` and must be filtered out

**Frontend**:
- All API calls defined in `frontend/src/api/index.ts` using existing `client` (Axios instance)
- New routes in `frontend/src/App.tsx`, new nav items in `frontend/src/components/Layout.tsx`
- CSS tokens only: `bg-card`, `bg-bg`, `bg-primary`, `text-text`, `text-text-secondary`, `border-border`
- Charts: Recharts with `stroke="var(--color-border)"`, `fill: 'var(--color-card)'`
- Icons: lucide-react exclusively

### Soft Constraints (conventions to follow)

- Models implement `to_dict()` method for API response serialization
- Seed endpoint pattern: `POST /seed` (as in `calendar.py`)
- Functional React components + hooks; no class components
- Date strings: ISO format `YYYY-MM-DD` between frontend and backend
- Collapsible sections: `ChevronDown`/`ChevronUp` icons (Calendar.tsx pattern)

---

## Dependencies

Implementation order (must be sequential where noted):

1. `MacroDataPoint` model → `HistoricalEvent` model (parallel)
2. Both models imported in `main.py` (after step 1)
3. `macro.py` router → `historical_events.py` router (parallel, after step 2)
4. Both routers registered in `router.py` (after step 3)
5. `frontend/src/api/index.ts` extended (after step 4)
6. `MacroIndicators.tsx` + `HistoricalEvents.tsx` (parallel, after step 5)
7. `App.tsx` + `Layout.tsx` updated (after step 6)

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| DGS10 is daily frequency; others monthly — mixed display | Frontend shows raw data points; X-axis uses `YYYY-MM-DD` slice; user sees natural gap in monthly charts |
| FRED CSV format may change | Defensive parser: skip rows where value != float |
| SQLite `create_all` doesn't migrate existing tables | New tables only; no schema changes to existing tables |
| `UniqueConstraint("series_id", "data_date")` may cause insert errors on refresh | Use `INSERT OR IGNORE` pattern (SQLite dialect) or catch `IntegrityError` and update |

---

## Success Criteria (Verifiable)

- [ ] `GET /api/macro/indicators` returns 5 series objects each with `latest` and `history` arrays
- [ ] `POST /api/macro/refresh` fetches from FRED and returns `{"updated": N}` within 30s
- [ ] `/macro` page displays 5 indicator cards with latest value and MoM change
- [ ] Time range selector (3M/6M/1Y/3Y) updates all charts without additional API calls
- [ ] `GET /api/historical-events/` returns list with `?category=` and `?search=` filters working
- [ ] `POST /api/historical-events/seed` imports 10 builtin events (idempotent)
- [ ] `DELETE /api/historical-events/{id}` returns 403 for builtin events, 204 for custom
- [ ] `/historical-events` page: category chips + search filter events in real-time
- [ ] Expandable event cards show full description + key metrics grid
- [ ] Add event modal with KeyMetricsEditor (dynamic rows, max 10) works correctly

---

## Files to Create/Modify

| File | Action | Notes |
|------|--------|-------|
| `backend/app/models/macro_indicator.py` | Create | `MacroDataPoint` model, UniqueConstraint |
| `backend/app/models/historical_event.py` | Create | `HistoricalEvent` model, is_builtin lock |
| `backend/app/main.py` | Modify | Import 2 new models (2 lines) |
| `backend/app/api/macro.py` | Create | FRED CSV fetch + GET/POST routes |
| `backend/app/api/historical_events.py` | Create | CRUD + seed (10 builtin events) |
| `backend/app/api/router.py` | Modify | Register 2 new routers |
| `frontend/src/api/index.ts` | Modify | Add `macroApi` + `historicalEventsApi` |
| `frontend/src/pages/MacroIndicators.tsx` | Create | 5 cards + collapsible charts |
| `frontend/src/pages/HistoricalEvents.tsx` | Create | List + filter + modal |
| `frontend/src/App.tsx` | Modify | 2 new routes |
| `frontend/src/components/Layout.tsx` | Modify | 2 new nav items |
