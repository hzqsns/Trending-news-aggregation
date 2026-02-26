import { useEffect, useState } from 'react'
import { Newspaper, AlertTriangle, TrendingUp, BarChart3 } from 'lucide-react'
import { dashboardApi, articlesApi } from '@/api'

interface Overview {
  today_articles: number
  active_alerts: number
  important_today: number
  sentiment: { overall_score: number; label: string }
  category_breakdown: Record<string, number>
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
  extreme_fear: '极度恐慌',
  fear: '恐慌',
  neutral: '中性',
  greed: '贪婪',
  extreme_greed: '极度贪婪',
}

const sentimentColors: Record<string, string> = {
  extreme_fear: 'text-danger',
  fear: 'text-warning',
  neutral: 'text-text-secondary',
  greed: 'text-success',
  extreme_greed: 'text-primary',
}

const categoryLabels: Record<string, string> = {
  a_stock: 'A股',
  global: '全球',
  crypto: '加密货币',
  tech: '科技',
  macro: '宏观',
  general: '综合',
}

export default function Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [trending, setTrending] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [ov, tr] = await Promise.all([
          dashboardApi.getOverview(),
          articlesApi.trending(10),
        ])
        setOverview(ov.data)
        setTrending(tr.data)
      } catch (e) {
        console.error('Failed to load dashboard', e)
      } finally {
        setLoading(false)
      }
    }
    load()
    const interval = setInterval(load, 60000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-text-secondary">加载中...</div>
  }

  return (
    <div>
      <h2 className="text-xl font-bold mb-6">Dashboard</h2>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard icon={Newspaper} label="今日新闻" value={overview?.today_articles ?? 0} color="bg-primary" />
        <StatCard icon={AlertTriangle} label="活跃预警" value={overview?.active_alerts ?? 0} color="bg-danger" />
        <StatCard icon={TrendingUp} label="重要事件" value={overview?.important_today ?? 0} color="bg-warning" />
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-lg bg-success/10">
              <BarChart3 size={20} className="text-success" />
            </div>
            <span className="text-sm text-text-secondary">市场情绪</span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold">{overview?.sentiment?.overall_score ?? 50}</span>
            <span className={`text-sm font-medium ${sentimentColors[overview?.sentiment?.label || 'neutral']}`}>
              {sentimentLabels[overview?.sentiment?.label || 'neutral'] || '中性'}
            </span>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      {overview?.category_breakdown && Object.keys(overview.category_breakdown).length > 0 && (
        <div className="bg-card rounded-xl p-5 shadow-sm border border-border mb-6">
          <h3 className="font-semibold mb-3">分类分布</h3>
          <div className="flex flex-wrap gap-2">
            {Object.entries(overview.category_breakdown).map(([cat, count]) => (
              <span key={cat} className="px-3 py-1 rounded-full bg-bg text-sm">
                {categoryLabels[cat] || cat}: <strong>{count}</strong>
              </span>
            ))}
          </div>
        </div>
      )}

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
              <a
                key={a.id}
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-3 p-4 hover:bg-bg/50 transition-colors"
              >
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
        <div className={`p-2 rounded-lg ${color}/10`}>
          <Icon size={20} className={color.replace('bg-', 'text-')} />
        </div>
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
    <span className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg text-sm ${c.cls}`}>
      {c.emoji}
    </span>
  )
}
