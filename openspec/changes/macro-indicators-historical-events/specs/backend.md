# Backend Specs

## MacroDataPoint Model
- File: `backend/app/models/macro_indicator.py`
- Table: `macro_data_points`
- Fields: id, series_id(String20), data_date(Date), value(Float nullable), yoy(Float nullable), mom(Float nullable), fetched_at(DateTime)
- Constraints: UniqueConstraint("series_id","data_date"), Index(series_id), Index(data_date)
- Method: `to_dict()` → dict with ISO date strings

## HistoricalEvent Model
- File: `backend/app/models/historical_event.py`
- Table: `historical_events`
- Fields: id, title(String200), category(String50), date_range(String50), market_impact(String20 default=mixed), description(Text nullable), key_metrics(JSONField nullable default=list), is_builtin(Boolean default=False), created_at(DateTime)
- Constraints: Index(category)
- Method: `to_dict()` → dict

## main.py changes
- Add: `from app.models.macro_indicator import MacroDataPoint  # noqa: F401`
- Add: `from app.models.historical_event import HistoricalEvent  # noqa: F401`
- Location: after existing model imports (near line 14-15)

## macro.py Router
- File: `backend/app/api/macro.py`
- FRED_SERIES dict with 5 series configs
- `_fetch_and_store_series(series_id, session)` async helper
  - httpx GET to FRED CSV URL
  - Parse CSV, filter "." values
  - Compute mom (abs diff with prev), yoy for CPIAUCSL (12-month lookback)
  - Insert via try/except IntegrityError → update on conflict
  - Return count of upserted records
- `GET /` → returns all 5 series with latest + history
  - Query last 400 points per series, ordered by data_date ASC
  - Compute trend from last 2 points (or "flat" if delta < 0.01)
- `POST /refresh` → calls _fetch_and_store_series for all 5 series
  - Returns `{"updated": total, "series": {id: count}}`
- Auth: both endpoints require `Depends(get_current_user)`

## historical_events.py Router
- File: `backend/app/api/historical_events.py`
- `GET /` → list all events
  - Optional query params: `category: str | None`, `search: str | None`
  - Filter by category (exact match) and search (title LIKE + description LIKE)
  - Return list ordered by date_range ASC
- `POST /` → create custom event
  - Validate: category ∈ valid set, market_impact ∈ {bullish, bearish, mixed}
  - Set is_builtin=False always on creation
- `DELETE /{id}` → delete event
  - If is_builtin=True: return HTTPException(403, "Cannot delete builtin event")
  - If not found: return HTTPException(404)
  - On success: return Response(status_code=204)
- `POST /seed` → import builtin events
  - Dedup by title (skip if already exists with is_builtin=True)
  - Returns `{"added": N, "skipped": M}`
- Auth: all endpoints require `Depends(get_current_user)`

## router.py changes
- Add import: `from app.api import macro, historical_events`
- Add: `api_router.include_router(macro.router, prefix="/macro", tags=["Macro"])`
- Add: `api_router.include_router(historical_events.router, prefix="/historical-events", tags=["HistoricalEvents"])`

## 10 Builtin Historical Events
1. 2008全球金融危机 | financial_crisis | 2008-09 ~ 2009-06 | bearish
2. 2020 COVID市场崩盘 | pandemic | 2020-02 ~ 2020-04 | bearish
3. 2000科技泡沫破裂 | tech_bubble | 2000-03 ~ 2002-10 | bearish
4. 1997亚洲金融危机 | financial_crisis | 1997-07 ~ 1998-12 | bearish
5. 2022加息周期 | monetary_policy | 2022-03 ~ 2023-07 | bearish
6. 2020量化宽松 | monetary_policy | 2020-03 ~ 2022-03 | bullish
7. 2010欧债危机 | financial_crisis | 2010-04 ~ 2012-07 | bearish
8. 2022俄乌冲突 | geopolitics | 2022-02 ~ 2022-12 | mixed
9. 2023美国银行业危机 | financial_crisis | 2023-03 ~ 2023-05 | bearish
10. 2024AI科技牛市 | tech_bubble | 2024-01 ~ 2024-12 | bullish
