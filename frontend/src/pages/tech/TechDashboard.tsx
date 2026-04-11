import { useState, useEffect } from 'react'
import { Newspaper, TrendingUp, Star } from 'lucide-react'
import { techApi } from '@/api/tech'
import { Card, CardHeader, CardTitle } from '@/components/ui'

interface DashboardData {
  total_articles: number
  articles_24h: number
  high_importance_24h: number
  top_sources: { source: string; count: number }[]
}

export default function TechDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)

  useEffect(() => {
    techApi.getDashboard().then((r) => setData(r.data)).catch(() => {})
  }, [])

  if (!data) {
    return <div className="flex items-center justify-center h-64 text-text-secondary">加载中...</div>
  }

  const stats = [
    { label: '总文章数', value: data.total_articles, icon: Newspaper, color: 'text-blue-500' },
    { label: '24h 新增', value: data.articles_24h, icon: TrendingUp, color: 'text-green-500' },
    { label: '24h 高价值', value: data.high_importance_24h, icon: Star, color: 'text-orange-500' },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">技术信息 Dashboard</h1>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <div className="flex items-center gap-3 mb-2">
              <s.icon size={20} className={s.color} />
              <span className="text-sm text-text-secondary">{s.label}</span>
            </div>
            <span className="text-2xl font-bold">{s.value}</span>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>数据源统计 (24h)</CardTitle>
        </CardHeader>
        {data.top_sources.length === 0 ? (
          <p className="text-sm text-text-secondary">暂无数据，等待首次采集</p>
        ) : (
          <div className="space-y-2">
            {data.top_sources.map((s) => (
              <div key={s.source} className="flex items-center justify-between text-sm">
                <span>{s.source}</span>
                <span className="font-medium">{s.count} 篇</span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
