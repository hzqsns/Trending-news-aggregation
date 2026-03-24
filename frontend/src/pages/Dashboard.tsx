import { useEffect, useState } from 'react'
import { Newspaper, AlertTriangle, TrendingUp, BarChart3, RefreshCw } from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { dashboardApi, articlesApi } from '@/api'
import { useNewsSocket } from '@/hooks/useNewsSocket'

interface Overview {
  today_articles: number
  active_alerts: number
  important_today: number
  sentiment: { overall_score: number; label: string }
  category_breakdown: Record<string, number>
}

interface SentimentPoint {
  snapshot_time: string
  overall_score: number
  label: string
}

interface HourlyPoint {
  hour: string
  count: number
}

interface SourceStat {
  source: string
  count: number
}

interface StatsData {
  total_articles: number
  sources: SourceStat[]
  hourly_volume: HourlyPoint[]
}

interface Article {
  id: number
  title: string
  source: string
  category: string
  importance: number
  sentiment: string | null
  published_at: string | null
  url: string
}

const sentimentLabels: Record<string, string> = {
  extreme_fear: '极度恐慌', fear: '恐慌', neutral: '中性',
  greed: '贪婪', extreme_greed: '极度贪婪', bullish: '看多', bearish: '看空',
}

const categoryLabels: Record<string, string> = {
  a_stock: 'A股', global: '全球', crypto: '加密货币', tech: '科技', macro: '宏观', general: '综合',
}

const PIE_COLORS = ['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']

export default function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [trending, setTrending] = useState<Article[]>([])
  const [sentimentHistory, setSentimentHistory] = useState<SentimentPoint[]>([])
  const [stats, setStats] = useState<StatsData | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const [ov, tr, sh, st] = await Promise.all([
        dashboardApi.getOverview(),
        articlesApi.trending(10),
        dashboardApi.getSentimentHistory(7),
        dashboardApi.getStats(),
      ])
      setOverview(ov.data)
      setTrending(tr.data)
      setSentimentHistory(sh.data)
      setStats(st.data)
    } catch (e) {
      console.error('Failed to load dashboard', e)
    } finally {
      setLoading(false)
    }
  }

  useNewsSocket({
    new_article: () => load(),
    new_alert: () => load(),
  })

  useEffect(() => {
    load()
    const interval = setInterval(load, 120_000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-text-secondary">加载中...</div>
  }

  const pieData = overview?.category_breakdown
    ? Object.entries(overview.category_breakdown).map(([name, value]) => ({
        name: categoryLabels[name] || name, value,
      }))
    : []

  const sentimentChartData = sentimentHistory.map((s) => ({
    time: s.snapshot_time?.slice(5, 16).replace('T', ' ') || '',
    score: s.overall_score,
  }))

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">Dashboard</h2>
        <button onClick={() => { setLoading(true); load() }} className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text">
          <RefreshCw size={14} /> 刷新
        </button>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard icon={Newspaper} label="今日新闻" value={overview?.today_articles ?? 0} color="bg-primary" />
        <StatCard icon={AlertTriangle} label="活跃预警" value={overview?.active_alerts ?? 0} color="bg-danger" />
        <StatCard icon={TrendingUp} label="重要事件" value={overview?.important_today ?? 0} color="bg-warning" />
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-success/10"><BarChart3 size={20} className="text-success" /></div>
            <span className="text-sm text-text-secondary">市场情绪</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold">{overview?.sentiment?.overall_score ?? 50}</span>
            <span className="text-sm font-medium text-text-secondary">
              {sentimentLabels[overview?.sentiment?.label || 'neutral'] || '中性'}
            </span>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* 24h Volume Chart */}
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
          <h3 className="font-semibold text-sm mb-4">24 小时新闻采集量</h3>
          {stats?.hourly_volume && stats.hourly_volume.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={stats.hourly_volume} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="hour" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} interval={2} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
                  labelFormatter={(l) => `${l}`}
                  formatter={(v: string | number | undefined) => [`${v ?? 0} 条`, '新闻数'] as [string, string]}
                />
                <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-text-secondary text-sm">暂无数据</div>
          )}
        </div>

        {/* Sentiment History Chart */}
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
          <h3 className="font-semibold text-sm mb-4">市场情绪趋势 (7 天)</h3>
          {sentimentChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={sentimentChartData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="sentimentGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} />
                <Tooltip
                  contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: string | number | undefined) => [`${v ?? 0}`, '情绪指数'] as [string, string]}
                />
                <Area type="monotone" dataKey="score" stroke="#10b981" strokeWidth={2} fill="url(#sentimentGrad)" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-text-secondary text-sm">暂无情绪数据，配置 AI 后将自动生成</div>
          )}
        </div>
      </div>

      {/* Source Distribution + Category Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        {/* Source Pie */}
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
          <h3 className="font-semibold text-sm mb-4">来源分布</h3>
          {stats?.sources && stats.sources.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={stats.sources.map((s) => ({ name: s.source, value: s.count }))}
                  cx="50%" cy="50%" innerRadius={50} outerRadius={90}
                  paddingAngle={2} dataKey="value"
                  label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
                >
                  {stats.sources.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: string | number | undefined) => [`${v ?? 0} 条`, '新闻数'] as [string, string]}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-text-secondary text-sm">暂无数据</div>
          )}
        </div>

        {/* Category Breakdown */}
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
          <h3 className="font-semibold text-sm mb-4">今日分类统计</h3>
          {pieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={pieData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis type="number" tick={{ fontSize: 11, fill: 'var(--color-text-secondary)' }} allowDecimals={false} />
                <YAxis dataKey="name" type="category" tick={{ fontSize: 12, fill: 'var(--color-text-secondary)' }} width={70} />
                <Tooltip
                  contentStyle={{ background: 'var(--color-card)', border: '1px solid var(--color-border)', borderRadius: 8, fontSize: 12 }}
                  formatter={(v: string | number | undefined) => [`${v ?? 0} 条`, '新闻数'] as [string, string]}
                />
                <Bar dataKey="value" radius={[0, 4, 4, 0]}>
                  {pieData.map((_, i) => (
                    <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-text-secondary text-sm">今日暂无分类数据</div>
          )}
        </div>
      </div>

      {/* Trending News */}
      <div className="bg-card rounded-xl shadow-sm border border-border">
        <div className="p-5 border-b border-border">
          <h3 className="font-semibold">🔥 热门新闻 Top 10</h3>
        </div>
        <div className="divide-y divide-border">
          {trending.length === 0 ? (
            <div className="p-8 text-center text-text-secondary">暂无新闻数据，系统采集后将自动展示</div>
          ) : (
            trending.map((a) => (
              <a key={a.id} href={a.url} target="_blank" rel="noopener noreferrer"
                className="flex items-start gap-3 p-4 hover:bg-bg/50 transition-colors">
                <ImportanceBadge level={a.importance} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{a.title}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-text-secondary">{a.source}</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-bg">{categoryLabels[a.category] || a.category}</span>
                    {a.sentiment && (
                      <span className={`text-xs ${a.sentiment === 'bullish' ? 'text-success' : a.sentiment === 'bearish' ? 'text-danger' : 'text-text-secondary'}`}>
                        {a.sentiment === 'bullish' ? '📈 看多' : a.sentiment === 'bearish' ? '📉 看空' : '➖ 中性'}
                      </span>
                    )}
                  </div>
                </div>
              </a>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

function StatCard({ icon: Icon, label, value, color }: { icon: React.ElementType; label: string; value: number; color: string }) {
  return (
    <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
      <div className="flex items-center gap-3 mb-2">
        <div className={`p-2 rounded-lg ${color}/10`}><Icon size={20} className={color.replace('bg-', 'text-')} /></div>
        <span className="text-sm text-text-secondary">{label}</span>
      </div>
      <span className="text-2xl font-bold">{value}</span>
    </div>
  )
}

function ImportanceBadge({ level }: { level: number }) {
  const config: Record<number, { emoji: string; cls: string }> = {
    5: { emoji: '🚨', cls: 'bg-danger/10 text-danger' },
    4: { emoji: '⚠️', cls: 'bg-warning/10 text-warning' },
    3: { emoji: '📢', cls: 'bg-primary/10 text-primary' },
    2: { emoji: '📰', cls: 'bg-bg text-text-secondary' },
    1: { emoji: '📄', cls: 'bg-bg text-text-secondary' },
    0: { emoji: '📄', cls: 'bg-bg text-text-secondary' },
  }
  const c = config[level] || config[0]
  return (
    <span className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-sm ${c.cls}`}>{c.emoji}</span>
  )
}
