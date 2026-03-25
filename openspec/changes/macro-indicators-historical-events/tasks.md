# Tasks: 宏观指标追踪 + 历史事件库

## Backend Tasks

- [x] 1.1 Create `backend/app/models/macro_indicator.py` with MacroDataPoint model (series_id, data_date, value, yoy, mom, UniqueConstraint)
- [x] 1.2 Create `backend/app/models/historical_event.py` with HistoricalEvent model (title, category, date_range, market_impact, key_metrics JSONField, is_builtin)
- [x] 1.3 Modify `backend/app/main.py` to import MacroDataPoint and HistoricalEvent (2 lines after existing model imports)
- [x] 1.4 Create `backend/app/api/macro.py` with FRED_SERIES config, _fetch_and_store_series helper, GET /indicators and POST /refresh endpoints
- [x] 1.5 Create `backend/app/api/historical_events.py` with GET / (filter), POST / (create), DELETE /{id} (403 for builtin), POST /seed (10 builtin events)
- [x] 1.6 Modify `backend/app/api/router.py` to register macro and historical_events routers

## Frontend Tasks

- [x] 2.1 Modify `frontend/src/api/index.ts` to add macroApi (getAll, refresh) and historicalEventsApi (list, create, remove, seed) with TypeScript interfaces
- [x] 2.2 Create `frontend/src/pages/MacroIndicators.tsx` with 5 IndicatorCards, TimeRangeSelector, CollapsibleCharts (Recharts LineChart, connectNulls=false)
- [x] 2.3 Create `frontend/src/pages/HistoricalEvents.tsx` with EventList, CategoryChips, SearchInput, expandable EventCards, AddEventModal with KeyMetricsEditor
- [x] 2.4 Modify `frontend/src/App.tsx` to add /macro and /historical-events routes
- [x] 2.5 Modify `frontend/src/components/Layout.tsx` to add TrendingUp (宏观指标) and History (历史事件库) nav items after CalendarDays
