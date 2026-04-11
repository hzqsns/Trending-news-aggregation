import { useState, useEffect, useCallback } from 'react'
import { ExternalLink, RefreshCw } from 'lucide-react'
import { techApi } from '@/api/tech'
import { Card } from '@/components/ui'
import { formatDistanceToNow } from 'date-fns'
import { zhCN } from 'date-fns/locale'

interface Article {
  id: number
  title: string
  url: string
  source: string
  summary: string | null
  importance: number
  fetched_at: string | null
}

interface Props {
  title: string
  sourceFilter?: string
  description?: string
}

export default function TechFeedPage({ title, sourceFilter, description }: Props) {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = { page, page_size: 20 }
      if (sourceFilter) params.source = sourceFilter
      const { data } = await techApi.getArticles(params)
      setArticles(data.items)
      setTotal(data.total)
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [page, sourceFilter])

  useEffect(() => { load() }, [load])

  const importanceColor = (n: number) =>
    n >= 4 ? 'text-red-500' : n >= 3 ? 'text-orange-500' : n >= 2 ? 'text-yellow-600' : 'text-text-secondary'

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">{title}</h1>
          {description && <p className="text-sm text-text-secondary mt-1">{description}</p>}
        </div>
        <button onClick={load} className="p-2 rounded-lg hover:bg-bg text-text-secondary hover:text-text transition-colors">
          <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <Card className="divide-y divide-border p-0 overflow-hidden">
        {loading && articles.length === 0 ? (
          <div className="flex items-center justify-center h-64 text-text-secondary">加载中...</div>
        ) : articles.length === 0 ? (
          <div className="p-8 text-center text-text-secondary">暂无数据，等待首次采集</div>
        ) : (
          articles.map((a) => (
            <a
              key={a.id}
              href={a.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-start gap-3 p-4 hover:bg-bg/50 transition-colors group"
            >
              <span className={`shrink-0 text-sm font-bold w-6 text-center ${importanceColor(a.importance)}`}>
                {a.importance}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium group-hover:text-primary transition-colors line-clamp-2">
                  {a.title}
                </div>
                {a.summary && (
                  <p className="text-xs text-text-secondary mt-1 line-clamp-2">{a.summary}</p>
                )}
                <div className="flex items-center gap-2 mt-1.5 text-xs text-text-secondary">
                  <span className="px-1.5 py-0.5 rounded bg-bg">{a.source}</span>
                  {a.fetched_at && (
                    <span>{formatDistanceToNow(new Date(a.fetched_at), { addSuffix: true, locale: zhCN })}</span>
                  )}
                </div>
              </div>
              <ExternalLink size={14} className="shrink-0 mt-1 text-text-secondary opacity-0 group-hover:opacity-100 transition-opacity" />
            </a>
          ))
        )}
      </Card>

      {total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40"
          >
            上一页
          </button>
          <span className="text-sm text-text-secondary">第 {page} 页</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={articles.length < 20}
            className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  )
}
