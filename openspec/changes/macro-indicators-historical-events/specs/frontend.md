# Frontend Specs

## api/index.ts additions

```typescript
export const macroApi = {
  getAll: () => client.get<MacroIndicator[]>('/macro/indicators'),
  refresh: () => client.post<{updated: number; series: Record<string, number>}>('/macro/refresh'),
}

export const historicalEventsApi = {
  list: (params: { category?: string; search?: string } = {}) =>
    client.get<HistoricalEvent[]>('/historical-events/', { params }),
  create: (data: CreateEventPayload) => client.post<HistoricalEvent>('/historical-events/', data),
  remove: (id: number) => client.delete(`/historical-events/${id}`),
  seed: () => client.post<{added: number; skipped: number}>('/historical-events/seed'),
}
```

## TypeScript Interfaces

```typescript
interface MacroIndicator {
  series_id: 'M2SL' | 'FEDFUNDS' | 'CPIAUCSL' | 'DGS10' | 'UNRATE'
  label: string
  unit: string
  latest_value: number | null
  latest_date: string
  mom: number | null
  yoy: number | null
  trend: 'up' | 'down' | 'flat'
  history: Array<{ data_date: string; value: number }>
}

interface HistoricalEvent {
  id: number
  title: string
  category: string
  date_range: string
  market_impact: 'bullish' | 'bearish' | 'mixed'
  description: string | null
  key_metrics: Array<{ label: string; value: string }>
  is_builtin: boolean
  created_at: string
}
```

## MacroIndicators.tsx

- Route: `/macro`
- Nav: TrendingUp icon, label "宏观指标"
- State: `indicators`, `loading`, `refreshing`, `timeRange`, `expandedCards`
- Initial load: `useEffect → macroApi.getAll()`
- RefreshButton: `refreshing=true → macroApi.refresh() → reload → refreshing=false`
- TimeRange chips: 3M/6M/1Y/3Y, default=1Y, client-side filter only
- IndicatorCard: latest_value + unit, MoM badge (colored TrendingUp/Down/Minus), expand button
- CollapsibleChart: LineChart, connectNulls=false, height=220, category X-axis
  - X-axis ticks: show every Nth label based on data density
  - Tooltip: value + unit
  - Line color: blue for M2SL, red for rate series
- Loading: skeleton placeholders (animate-pulse)
- Empty state: "暂无数据，点击刷新获取"

## HistoricalEvents.tsx

- Route: `/historical-events`
- Nav: TrendingDown icon, label "历史事件库"
- State: `events`, `loading`, `filterCategory`, `searchQuery`, `expandedId`, `showAddModal`, `addForm`, `adding`, `addError`
- Initial load: `useEffect → historicalEventsApi.list()`
- Filter: client-side after load (category chip + debounced 300ms search)
- EventCard:
  - Header: title + CategoryBadge + MarketImpactBadge + (Lock or Trash2) + expand toggle
  - Collapsed: date_range + description (line-clamp-2)
  - Expanded: full description + KeyMetricsGrid + tags list
  - is_builtin=true: Lock icon, no delete button
  - is_builtin=false: Trash2 button (calls remove)
- "导入内置事件" button → historicalEventsApi.seed() → reload
- AddEventModal: title/category/dateRange/marketImpact/description/key_metrics/tags
  - KeyMetricsEditor: [{label, value}] dynamic rows, Plus button, × per row, max 10
  - Validation: title required, category required
  - On submit: historicalEventsApi.create() → close modal + reload

## App.tsx additions
```tsx
import MacroIndicators from '@/pages/MacroIndicators'
import HistoricalEvents from '@/pages/HistoricalEvents'
// inside Routes:
<Route path="/macro" element={<MacroIndicators />} />
<Route path="/historical-events" element={<HistoricalEvents />} />
```

## Layout.tsx additions
```tsx
import { TrendingUp, TrendingDown } from 'lucide-react'
// in navItems after CalendarDays:
{ to: '/macro', icon: TrendingUp, label: '宏观指标' },
{ to: '/historical-events', icon: TrendingDown, label: '历史事件库' },
```
