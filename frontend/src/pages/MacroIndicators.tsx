import { useEffect, useState, useMemo } from 'react'
import { TrendingUp, TrendingDown, Minus, RefreshCw, ChevronDown, ChevronUp, Sparkles } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { macroApi } from '@/api'

interface MacroDataPoint {
  data_date: string
  value: number
}

interface MacroIndicator {
  series_id: string
  label: string
  unit: string
  latest_value: number | null
  latest_date: string | null
  mom: number | null
  yoy: number | null
  trend: 'up' | 'down' | 'flat'
  history: MacroDataPoint[]
}

interface AssetImpact {
  asset: string
  direction: 'bullish' | 'bearish' | 'neutral'
  reason: string
}

interface MacroAnalysis {
  environment: string
  summary: string
  impacts: AssetImpact[]
  generated_at: string
  cached: boolean
  error?: string
}

type TimeRange = '3M' | '6M' | '1Y' | '3Y' | '5Y' | 'ALL' | 'CUSTOM'

const TIME_RANGE_MONTHS: Partial<Record<TimeRange, number>> = {
  '3M': 3, '6M': 6, '1Y': 12, '3Y': 36, '5Y': 60,
}
const TIME_RANGES: TimeRange[] = ['3M', '6M', '1Y', '3Y', '5Y', 'ALL', 'CUSTOM']
const TIME_RANGE_LABELS: Record<TimeRange, string> = {
  '3M': '3M', '6M': '6M', '1Y': '1Y', '3Y': '3Y', '5Y': '5Y', 'ALL': '全部', 'CUSTOM': '自定义',
}

const LINE_COLORS: Record<string, string> = {
  M2SL: '#3b82f6',
  FEDFUNDS: '#ef4444',
  CPIAUCSL: '#f59e0b',
  DGS10: '#8b5cf6',
  UNRATE: '#10b981',
}

const ENV_COLORS: Record<string, string> = {
  宽松: 'text-success bg-success/10 border-success/20',
  中性: 'text-text-secondary bg-bg border-border',
  偏紧: 'text-amber-500 bg-amber-500/10 border-amber-500/20',
  紧缩: 'text-danger bg-danger/10 border-danger/20',
}

const DIRECTION_CONFIG = {
  bullish: { label: '利多', cls: 'text-success bg-success/10 border-success/20', icon: TrendingUp },
  bearish: { label: '利空', cls: 'text-danger bg-danger/10 border-danger/20', icon: TrendingDown },
  neutral: { label: '中性', cls: 'text-text-secondary bg-bg border-border', icon: Minus },
}

function filterHistory(
  history: MacroDataPoint[],
  range: TimeRange,
  customStart: string,
  customEnd: string,
): MacroDataPoint[] {
  if (range === 'ALL') return history
  if (range === 'CUSTOM') {
    const start = customStart ? new Date(customStart) : null
    const end = customEnd ? new Date(customEnd) : null
    return history.filter((p) => {
      const d = new Date(p.data_date)
      if (start && d < start) return false
      if (end && d > end) return false
      return true
    })
  }
  const months = TIME_RANGE_MONTHS[range]
  if (!months) return history
  const cutoff = new Date()
  cutoff.setMonth(cutoff.getMonth() - months)
  return history.filter((p) => new Date(p.data_date) >= cutoff)
}

function MoMBadge({ indicator }: { indicator: MacroIndicator }) {
  const val = indicator.series_id === 'CPIAUCSL' ? indicator.yoy : indicator.mom
  const label = indicator.series_id === 'CPIAUCSL' ? '同比' : 'MoM'
  if (val === null || val === undefined) return null
  const { trend } = indicator
  const colorCls = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-danger' : 'text-text-secondary'
  const Icon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const sign = val > 0 ? '+' : ''
  return (
    <span className={`flex items-center gap-1 text-xs ${colorCls}`}>
      <Icon size={12} />
      {sign}{val.toFixed(2)} {indicator.unit} ({label})
    </span>
  )
}

function IndicatorCard({
  indicator, expanded, onToggle,
}: {
  indicator: MacroIndicator
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <div
      className={`bg-card rounded-xl border p-5 cursor-pointer transition-colors hover:border-primary/50 ${expanded ? 'border-primary' : 'border-border'}`}
      onClick={onToggle}
    >
      <div className="flex items-start justify-between mb-1">
        <span className="text-xs text-text-secondary">{indicator.label}</span>
        {expanded ? <ChevronUp size={14} className="text-text-secondary mt-0.5" /> : <ChevronDown size={14} className="text-text-secondary mt-0.5" />}
      </div>
      <div className="flex items-baseline gap-1.5 mb-1">
        <span className="text-2xl font-bold">
          {indicator.latest_value !== null ? indicator.latest_value.toLocaleString() : '—'}
        </span>
        <span className="text-xs text-text-secondary">{indicator.unit}</span>
      </div>
      <MoMBadge indicator={indicator} />
      {indicator.latest_date && (
        <p className="text-xs text-text-secondary mt-1">{indicator.latest_date.slice(0, 7)}</p>
      )}
    </div>
  )
}

function CollapsibleChart({
  indicator, timeRange, customStart, customEnd,
}: {
  indicator: MacroIndicator
  timeRange: TimeRange
  customStart: string
  customEnd: string
}) {
  const data = useMemo(
    () => filterHistory(indicator.history, timeRange, customStart, customEnd),
    [indicator.history, timeRange, customStart, customEnd],
  )
  const color = LINE_COLORS[indicator.series_id] || '#3b82f6'
  const label = TIME_RANGE_LABELS[timeRange] || timeRange

  if (data.length === 0) {
    return (
      <div className="bg-card rounded-xl border border-border p-5">
        <h3 className="text-sm font-semibold mb-3">{indicator.label} 历史趋势</h3>
        <div className="h-[200px] flex items-center justify-center text-text-secondary text-sm">暂无数据</div>
      </div>
    )
  }

  const tickInterval = data.length > 60 ? Math.floor(data.length / 12) : data.length > 24 ? 2 : 1

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <h3 className="text-sm font-semibold mb-3">{indicator.label} 历史趋势 ({label})</h3>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
          <XAxis
            dataKey="data_date"
            tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
            tickFormatter={(v: string) => v.slice(0, 7)}
            interval={tickInterval}
          />
          <YAxis
            tick={{ fontSize: 10, fill: 'var(--color-text-secondary)' }}
            domain={['auto', 'auto']}
            tickFormatter={(v: number) => v.toLocaleString()}
          />
          <Tooltip
            contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
            labelFormatter={(l: unknown) => String(l).slice(0, 10)}
            formatter={(v: unknown) => [`${(v as number).toLocaleString()} ${indicator.unit}`, indicator.label]}
          />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            activeDot={{ r: 4 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function MacroAnalysisPanel({ indicators }: { indicators: MacroIndicator[] }) {
  const [analysis, setAnalysis] = useState<MacroAnalysis | null>(null)
  const [loading, setLoading] = useState(false)

  const hasData = indicators.some((i) => i.latest_value !== null)

  const generate = async (force = false) => {
    setLoading(true)
    try {
      const resp = await macroApi.getAnalysis(force)
      setAnalysis(resp.data)
    } catch {
      setAnalysis({ environment: '', summary: '', impacts: [], generated_at: '', cached: false, error: 'AI 分析请求失败' })
    } finally {
      setLoading(false)
    }
  }

  if (!hasData) return null

  return (
    <div className="bg-card rounded-xl border border-border p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-primary" />
          <h3 className="text-sm font-semibold">AI 宏观分析</h3>
          {analysis?.cached && (
            <span className="text-xs text-text-secondary bg-bg border border-border px-2 py-0.5 rounded">缓存</span>
          )}
          {analysis?.generated_at && (
            <span className="text-xs text-text-secondary">
              {new Date(analysis.generated_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {analysis && (
            <button
              onClick={() => generate(true)}
              disabled={loading}
              className="flex items-center gap-1 text-xs text-text-secondary hover:text-text px-2 py-1 border border-border rounded-lg disabled:opacity-50"
            >
              <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
              重新生成
            </button>
          )}
          {!analysis && (
            <button
              onClick={() => generate(false)}
              disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-white rounded-lg text-xs hover:opacity-90 disabled:opacity-50"
            >
              <Sparkles size={12} />
              {loading ? '分析中...' : '生成 AI 分析'}
            </button>
          )}
        </div>
      </div>

      {loading && !analysis && (
        <div className="flex items-center gap-2 text-text-secondary text-sm py-4">
          <RefreshCw size={14} className="animate-spin" />
          正在调用 AI 分析当前宏观环境...
        </div>
      )}

      {analysis?.error && (
        <p className="text-danger text-sm">{analysis.error}</p>
      )}

      {analysis && !analysis.error && (
        <div className="space-y-4">
          <div className="flex items-start gap-3">
            {analysis.environment && (
              <span className={`shrink-0 text-xs px-2.5 py-1 rounded-full border font-medium ${ENV_COLORS[analysis.environment] || 'text-text-secondary bg-bg border-border'}`}>
                {analysis.environment}
              </span>
            )}
            <p className="text-sm text-text-secondary leading-relaxed">{analysis.summary}</p>
          </div>

          {analysis.impacts && analysis.impacts.length > 0 && (
            <div>
              <p className="text-xs text-text-secondary mb-2">各类资产影响</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2">
                {analysis.impacts.map((item) => {
                  const cfg = DIRECTION_CONFIG[item.direction] || DIRECTION_CONFIG.neutral
                  const Icon = cfg.icon
                  return (
                    <div key={item.asset} className="bg-bg rounded-lg border border-border p-3">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-xs font-medium">{item.asset}</span>
                        <span className={`flex items-center gap-0.5 text-xs px-1.5 py-0.5 rounded border ${cfg.cls}`}>
                          <Icon size={10} />
                          {cfg.label}
                        </span>
                      </div>
                      <p className="text-xs text-text-secondary leading-snug">{item.reason}</p>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function MacroIndicators() {
  const [indicators, setIndicators] = useState<MacroIndicator[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [timeRange, setTimeRange] = useState<TimeRange>('1Y')
  const [customStart, setCustomStart] = useState('')
  const [customEnd, setCustomEnd] = useState('')
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set(['M2SL']))

  const load = async () => {
    try {
      const resp = await macroApi.getAll()
      setIndicators(resp.data)
    } catch (e) {
      console.error('Failed to load macro indicators', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await macroApi.refresh()
      await load()
    } catch (e) {
      console.error('Refresh failed', e)
    } finally {
      setRefreshing(false)
    }
  }

  const toggleExpand = (series_id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(series_id)) next.delete(series_id)
      else next.add(series_id)
      return next
    })
  }

  const isCustom = timeRange === 'CUSTOM'

  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">宏观指标</h2>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl border border-border p-5 animate-pulse h-28" />
          ))}
        </div>
        <div className="bg-card rounded-xl border border-border p-5 animate-pulse h-48" />
      </div>
    )
  }

  const expandedIndicators = indicators.filter((ind) => expandedIds.has(ind.series_id))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">宏观指标</h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 px-3 py-2 border border-border rounded-lg text-sm hover:bg-bg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? '刷新中...' : '刷新数据'}
        </button>
      </div>

      {/* Time Range Selector */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <span className="text-sm text-text-secondary">时间范围：</span>
        <div className="flex flex-wrap gap-1 bg-card rounded-xl p-1 border border-border">
          {TIME_RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                timeRange === r ? 'bg-primary text-white' : 'text-text-secondary hover:text-text'
              }`}
            >
              {TIME_RANGE_LABELS[r]}
            </button>
          ))}
        </div>
        {isCustom && (
          <div className="flex items-center gap-2 text-sm">
            <input
              type="date"
              value={customStart}
              onChange={(e) => setCustomStart(e.target.value)}
              className="bg-card border border-border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:border-primary"
            />
            <span className="text-text-secondary">—</span>
            <input
              type="date"
              value={customEnd}
              onChange={(e) => setCustomEnd(e.target.value)}
              className="bg-card border border-border rounded-lg px-2 py-1.5 text-sm focus:outline-none focus:border-primary"
            />
          </div>
        )}
      </div>

      {/* Indicator Cards */}
      {indicators.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <TrendingUp size={40} className="mx-auto mb-3 text-text-secondary opacity-40" />
          <p className="text-text-secondary text-sm">暂无数据</p>
          <p className="text-text-secondary text-xs mt-1">点击右上角「刷新数据」从 FRED 获取宏观指标数据</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
            {indicators.map((ind) => (
              <IndicatorCard
                key={ind.series_id}
                indicator={ind}
                expanded={expandedIds.has(ind.series_id)}
                onToggle={() => toggleExpand(ind.series_id)}
              />
            ))}
          </div>

          {/* Expanded Charts */}
          {expandedIndicators.length > 0 && (
            <div className="space-y-4 mb-6">
              {expandedIndicators.map((ind) => (
                <CollapsibleChart
                  key={ind.series_id}
                  indicator={ind}
                  timeRange={timeRange}
                  customStart={customStart}
                  customEnd={customEnd}
                />
              ))}
            </div>
          )}

          {/* AI Analysis */}
          <MacroAnalysisPanel indicators={indicators} />
        </>
      )}
    </div>
  )
}
