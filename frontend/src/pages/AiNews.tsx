import { useEffect, useState, useCallback } from 'react'
import { Zap, ExternalLink, Search, RefreshCw } from 'lucide-react'
import { articlesApi } from '@/api'
import { Card, CardHeader, CardTitle, Loading, Empty, Input, useToast } from '@/components/ui'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface Article {
  id: number
  title: string
  url: string
  source: string
  summary: string | null
  importance: number
  sentiment: string | null
  published_at: string | null
  fetched_at: string | null
  ai_analysis: { reason?: string } | null
  tags: string[]
}

const IMPORTANCE_LABELS: Record<number, { label: string; color: string; emoji: string }> = {
  5: { label: '重大', color: 'bg-red-500/10 text-red-500 border-red-500/30', emoji: '🚨' },
  4: { label: '高', color: 'bg-orange-500/10 text-orange-500 border-orange-500/30', emoji: '⚠️' },
  3: { label: '中', color: 'bg-amber-500/10 text-amber-600 border-amber-500/30', emoji: '📢' },
  2: { label: '一般', color: 'bg-blue-500/10 text-blue-500 border-blue-500/30', emoji: '🤖' },
  1: { label: '低', color: 'bg-gray-500/10 text-gray-500 border-gray-500/30', emoji: '📰' },
  0: { label: '—', color: 'bg-gray-500/10 text-gray-500 border-gray-500/30', emoji: '📰' },
}

export default function AiNews() {
  const [items, setItems] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [hours, setHours] = useState<24 | 72 | 168>(24)
  const [importanceMin, setImportanceMin] = useState<2 | 3 | 4>(2)
  const [search, setSearch] = useState('')
  const toast = useToast()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await articlesApi.aiNews({
        hours,
        importance_min: importanceMin,
        limit: 50,
        ...(search ? { search } : {}),
      })
      setItems(data.items)
    } catch {
      toast.error('加载失败')
    } finally {
      setLoading(false)
    }
  }, [hours, importanceMin, search, toast])

  useEffect(() => {
    load()
  }, [load])

  // 按重要度分组
  const grouped: Record<number, Article[]> = {}
  items.forEach((item) => {
    grouped[item.importance] = grouped[item.importance] ?? []
    grouped[item.importance].push(item)
  })

  const sortedImportance = Object.keys(grouped)
    .map(Number)
    .sort((a, b) => b - a)

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Zap size={20} className="text-amber-500" />
          <h1 className="text-xl font-bold">AI 行业快讯</h1>
          <span className="text-xs text-text-secondary">
            · {items.length} 条（{hours === 24 ? '24h' : hours === 72 ? '3d' : '7d'}）
          </span>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 rounded-lg hover:bg-bg text-text-secondary hover:text-text transition-colors disabled:opacity-50"
          title="刷新"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <Card className="p-4">
        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex gap-1 bg-bg rounded-lg p-1">
            {[
              { v: 24, l: '24h' },
              { v: 72, l: '3d' },
              { v: 168, l: '7d' },
            ].map((opt) => (
              <button
                key={opt.v}
                onClick={() => setHours(opt.v as 24 | 72 | 168)}
                className={`px-3 py-1 text-xs rounded ${
                  hours === opt.v ? 'bg-primary text-white' : 'text-text-secondary'
                }`}
              >
                {opt.l}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-bg rounded-lg p-1">
            {[
              { v: 2, l: '全部' },
              { v: 3, l: '重要' },
              { v: 4, l: '关键' },
            ].map((opt) => (
              <button
                key={opt.v}
                onClick={() => setImportanceMin(opt.v as 2 | 3 | 4)}
                className={`px-3 py-1 text-xs rounded ${
                  importanceMin === opt.v ? 'bg-primary text-white' : 'text-text-secondary'
                }`}
              >
                {opt.l}
              </button>
            ))}
          </div>
          <div className="relative flex-1 min-w-[200px]">
            <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-secondary" />
            <Input
              type="text"
              placeholder="搜索 AI 公司 / 模型 / 事件"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-8 text-sm"
            />
          </div>
        </div>
      </Card>

      {loading ? (
        <Loading />
      ) : items.length === 0 ? (
        <Empty>
          暂无 AI 行业快讯。首次启用需等待 15 分钟后数据抓取完成（或检查系统设置中 RSS 源是否启用）
        </Empty>
      ) : (
        <div className="space-y-6">
          {sortedImportance.map((imp) => {
            const conf = IMPORTANCE_LABELS[imp]
            const bucket = grouped[imp]
            return (
              <Card key={imp}>
                <CardHeader>
                  <CardTitle>
                    <span className="mr-2">{conf.emoji}</span>
                    {conf.label}重要度 · {bucket.length} 条
                  </CardTitle>
                </CardHeader>
                <div className="divide-y divide-border -mx-6">
                  {bucket.map((a) => (
                    <a
                      key={a.id}
                      href={a.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-start gap-3 px-6 py-3 hover:bg-bg/50 transition-colors group"
                    >
                      <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border ${conf.color}`}>
                        {conf.label}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium group-hover:text-primary transition-colors line-clamp-2">
                          {a.title}
                        </div>
                        {a.ai_analysis?.reason && (
                          <p className="text-xs text-text-secondary mt-1 line-clamp-1">
                            💡 {a.ai_analysis.reason}
                          </p>
                        )}
                        {a.summary && !a.ai_analysis?.reason && (
                          <p className="text-xs text-text-secondary mt-1 line-clamp-2">{a.summary}</p>
                        )}
                        <div className="flex items-center gap-2 mt-1.5 text-xs text-text-secondary">
                          <span className="px-1.5 py-0.5 rounded bg-bg">{a.source}</span>
                          {a.sentiment && (
                            <span
                              className={
                                a.sentiment === 'bullish'
                                  ? 'text-green-500'
                                  : a.sentiment === 'bearish'
                                    ? 'text-red-500'
                                    : ''
                              }
                            >
                              {a.sentiment === 'bullish' ? '看多' : a.sentiment === 'bearish' ? '看空' : '中性'}
                            </span>
                          )}
                          {a.published_at && (
                            <span>
                              {formatDistanceToNow(new Date(a.published_at), {
                                addSuffix: true,
                                locale: zhCN,
                              })}
                            </span>
                          )}
                        </div>
                      </div>
                      <ExternalLink
                        size={14}
                        className="shrink-0 mt-1 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity"
                      />
                    </a>
                  ))}
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
