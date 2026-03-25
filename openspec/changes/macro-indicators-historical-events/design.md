# Design: 宏观指标追踪 + 历史事件库

## Architecture Overview

### Backend Design

#### MacroDataPoint Model (`macro_data_points` table)
```
id          INTEGER PK autoincrement
series_id   STRING(20) NOT NULL          -- "M2SL" | "FEDFUNDS" | "CPIAUCSL" | "DGS10" | "UNRATE"
data_date   DATE NOT NULL
value       FLOAT nullable               -- null if FRED returns "."
yoy         FLOAT nullable               -- YoY % (CPIAUCSL only, others null)
mom         FLOAT nullable               -- MoM absolute diff
fetched_at  DATETIME default=utcnow
UNIQUE(series_id, data_date)
INDEX(series_id), INDEX(data_date)
```

#### HistoricalEvent Model (`historical_events` table)
```
id            INTEGER PK autoincrement
title         STRING(200) NOT NULL
category      STRING(50) NOT NULL        -- financial_crisis|monetary_policy|pandemic|tech_bubble|geopolitics
date_range    STRING(50) NOT NULL        -- "2008-09 ~ 2009-03"
market_impact STRING(20) NOT NULL        -- bullish|bearish|mixed
description   TEXT nullable
key_metrics   JSONField                  -- [{"label": str, "value": str}]
is_builtin    BOOLEAN default=False      -- True = locked, DELETE returns 403
created_at    DATETIME default=utcnow
INDEX(category)
```

### API Design

#### Macro Router (`/api/macro`)
```
GET  /api/macro/indicators
  Response: [{
    series_id: str,
    label: str,
    unit: str,
    latest_value: float | null,
    latest_date: str,  # YYYY-MM-DD
    mom: float | null,
    yoy: float | null,  # CPIAUCSL only
    trend: "up" | "down" | "flat",
    history: [{"data_date": str, "value": float}]  # up to 400 points
  }]

POST /api/macro/refresh
  Triggers FRED CSV fetch for all 5 series
  Response: {"updated": N, "series": {"M2SL": M, ...}}
```

#### Historical Events Router (`/api/historical-events`)
```
GET    /api/historical-events/          # ?category=&search=
POST   /api/historical-events/          # Create custom event
DELETE /api/historical-events/{id}      # 403 if is_builtin, 204 if custom
POST   /api/historical-events/seed      # Import 10 builtin events (idempotent)
```

### FRED Data Fetch Strategy
- URL: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIES_ID>`
- No API key required
- Parse: skip header row, filter rows where value == "."
- MoM: `value[i] - value[i-1]` (absolute diff)
- YoY (CPIAUCSL): `(value[i] / value[i-12] - 1) * 100` using date arithmetic
- Upsert via: check existing by series_id+data_date, insert if not exists, update value if changed

### Frontend Design

#### MacroIndicators Page (`/macro`)
State:
```typescript
indicators: MacroIndicator[]  // from GET /macro/indicators
loading: boolean
refreshing: boolean
timeRange: '3M' | '6M' | '1Y' | '3Y'  // client-side filter only
expandedCards: Set<string>  // series_id set
```

Component hierarchy:
```
MacroIndicators
├── PageHeader (title + RefreshButton)
├── TimeRangeSelector (chip group)
├── IndicatorGrid (5 cards, grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 → actually 3+2)
│   └── IndicatorCard × 5
│       ├── value + unit
│       ├── MoMBadge (TrendingUp/TrendingDown/Minus)
│       └── expand button
└── ChartSection
    └── CollapsibleChart × 5
        └── LineChart (Recharts, connectNulls=false, category X-axis)
```

Chart data filter (frontend):
```typescript
function filterHistory(history, range) {
  const cutoff = subMonths(new Date(), {3M:3, 6M:6, 1Y:12, 3Y:36}[range])
  return history.filter(p => new Date(p.data_date) >= cutoff)
}
```

#### HistoricalEvents Page (`/historical-events`)
State:
```typescript
events: HistoricalEvent[]
loading: boolean
filterCategory: string  // '' = all
searchQuery: string     // debounced 300ms
expandedId: number | null
showAddModal: boolean
addForm: AddEventForm
adding: boolean
addError: string | null
```

Filtering (client-side after initial load):
```typescript
const filtered = events
  .filter(e => !filterCategory || e.category === filterCategory)
  .filter(e => !searchQuery ||
    e.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (e.description || '').toLowerCase().includes(searchQuery.toLowerCase()))
```

KeyMetricsEditor: isolated state `[{label, value}]`, max 10 rows, Plus/X buttons.

## Resolved Constraints

1. **FRED CSV**: No API key, free endpoint, "." = missing value
2. **Upsert strategy**: INSERT OR IGNORE (SQLite) via try/except IntegrityError
3. **Mixed frequency**: Display as-is, no normalization needed
4. **Charts**: `connectNulls={false}`, category X-axis, front-end time slice
5. **Builtin lock**: Backend returns 403 on DELETE for is_builtin=True events
6. **Seed idempotency**: Deduplicate by title + is_builtin=True before insert

## PBT Properties

| Property | Invariant | Falsification |
|----------|-----------|---------------|
| Upsert idempotency | POST /macro/refresh twice = same data | Call refresh 10x, compare counts |
| Builtin lock | DELETE builtin always → 403 | Send DELETE for all builtin IDs |
| Seed idempotency | Seed N times = same event count | Seed 3x, assert count unchanged |
| History monotonicity | data_date ascending in GET response | Check dates are sorted |
| Time filter completeness | filter(3M) ⊆ filter(6M) ⊆ filter(1Y) | Verify subset relationship |
