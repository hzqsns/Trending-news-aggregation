import { useEffect, useState } from 'react'
import { Search, RefreshCw, ExternalLink, Bookmark, BookmarkCheck, X, Tag } from 'lucide-react'
import { articlesApi, bookmarksApi } from '@/api'

interface Article {
  id: number
  title: string
  url: string
  source: string
  category: string
  summary: string | null
  importance: number
  sentiment: string | null
  tags: string[]
  published_at: string | null
  fetched_at: string | null
}

interface PaginatedResult {
  items: Article[]
  total: number
  page: number
  pages: number
}

const categoryLabels: Record<string, string> = {
  a_stock: 'A股', global: '全球', crypto: '加密货币', tech: '科技', macro: '宏观', general: '综合',
}

export default function NewsFeed() {
  const [data, setData] = useState<PaginatedResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [importance, setImportance] = useState(0)
  const [page, setPage] = useState(1)
  const [categories, setCategories] = useState<{category: string; count: number}[]>([])
  const [bookmarks, setBookmarks] = useState<Record<number, any>>({})
  const [activeBookmark, setActiveBookmark] = useState<number | null>(null)
  const [bookmarkNote, setBookmarkNote] = useState('')
  const [bookmarkTags, setBookmarkTags] = useState('')
  const [bookmarkSaving, setBookmarkSaving] = useState(false)

  const loadArticles = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page, page_size: 30, hours: 72 }
      if (search) params.search = search
      if (category) params.category = category
      if (importance > 0) params.importance_min = importance
      const resp = await articlesApi.list(params)
      setData(resp.data)
      if (resp.data?.items?.length) {
        const ids = resp.data.items.map((a: Article) => a.id)
        bookmarksApi.status(ids).then((r) => setBookmarks(r.data)).catch(() => {})
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    articlesApi.categories().then((r) => setCategories(r.data)).catch(() => {})
  }, [])

  useEffect(() => { loadArticles() }, [page, category, importance])

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setPage(1)
    loadArticles()
  }

  const openBookmarkPanel = (articleId: number) => {
    const existing = bookmarks[articleId]
    setBookmarkNote(existing?.note ?? '')
    setBookmarkTags((existing?.tags ?? []).join(', '))
    setActiveBookmark(articleId)
  }

  const closeBookmarkPanel = () => setActiveBookmark(null)

  const saveBookmark = async (articleId: number) => {
    setBookmarkSaving(true)
    const tags = bookmarkTags.split(',').map(t => t.trim()).filter(Boolean)
    try {
      if (bookmarks[articleId]) {
        await bookmarksApi.update(articleId, bookmarkNote || null, tags)
      } else {
        await bookmarksApi.create(articleId, bookmarkNote || undefined, tags)
      }
      const ids = data?.items.map(a => a.id) ?? []
      const r = await bookmarksApi.status(ids)
      setBookmarks(r.data)
      setActiveBookmark(null)
    } catch (e) {
      console.error(e)
    } finally {
      setBookmarkSaving(false)
    }
  }

  const removeBookmark = async (articleId: number) => {
    try {
      await bookmarksApi.remove(articleId)
      setBookmarks(prev => ({ ...prev, [articleId]: null }))
      setActiveBookmark(null)
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">新闻流</h2>
        <button onClick={loadArticles} className="flex items-center gap-1.5 text-sm text-text-secondary hover:text-text">
          <RefreshCw size={14} /> 刷新
        </button>
      </div>

      {/* Filters */}
      <div className="bg-card rounded-xl p-4 shadow-sm border border-border mb-4">
        <div className="flex flex-wrap items-center gap-3">
          <form onSubmit={handleSearch} className="flex-1 min-w-[200px]">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="搜索新闻..."
                className="w-full pl-9 pr-4 py-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
          </form>
          <select
            value={category}
            onChange={(e) => { setCategory(e.target.value); setPage(1) }}
            className="px-3 py-2 rounded-lg border border-border text-sm bg-white focus:outline-none"
          >
            <option value="">全部分类</option>
            {categories.map((c) => (
              <option key={c.category} value={c.category}>
                {categoryLabels[c.category] || c.category} ({c.count})
              </option>
            ))}
          </select>
          <select
            value={importance}
            onChange={(e) => { setImportance(Number(e.target.value)); setPage(1) }}
            className="px-3 py-2 rounded-lg border border-border text-sm bg-white focus:outline-none"
          >
            <option value={0}>全部重要度</option>
            <option value={3}>重要 (≥3)</option>
            <option value={4}>高度重要 (≥4)</option>
            <option value={5}>紧急 (5)</option>
          </select>
        </div>
      </div>

      {/* Articles List */}
      <div className="bg-card rounded-xl shadow-sm border border-border">
        {loading ? (
          <div className="p-8 text-center text-text-secondary">加载中...</div>
        ) : !data?.items?.length ? (
          <div className="p-8 text-center text-text-secondary">暂无新闻</div>
        ) : (
          <>
            <div className="divide-y divide-border">
              {data.items.map((a) => (
                <div key={a.id} className="p-4 hover:bg-bg/50 transition-colors relative">
                  <div className="flex items-start gap-3">
                    <span className="shrink-0 mt-0.5 text-sm">
                      {a.importance >= 4 ? '🚨' : a.importance >= 3 ? '⚠️' : '📰'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <a href={a.url} target="_blank" rel="noopener noreferrer" className="text-sm font-medium hover:text-primary flex items-center gap-1">
                        {a.title}
                        <ExternalLink size={12} className="shrink-0 text-text-secondary" />
                      </a>
                      {a.summary && <p className="text-xs text-text-secondary mt-1 line-clamp-2">{a.summary}</p>}
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className="text-xs px-1.5 py-0.5 rounded bg-bg">{a.source}</span>
                        <span className="text-xs px-1.5 py-0.5 rounded bg-bg">{categoryLabels[a.category] || a.category}</span>
                        {a.sentiment && (
                          <span className={`text-xs ${a.sentiment === 'bullish' ? 'text-success' : a.sentiment === 'bearish' ? 'text-danger' : 'text-text-secondary'}`}>
                            {a.sentiment === 'bullish' ? '看多' : a.sentiment === 'bearish' ? '看空' : '中性'}
                          </span>
                        )}
                        {a.tags?.map((t) => <span key={t} className="text-xs text-primary">#{t}</span>)}
                        <span className="text-xs text-text-secondary ml-auto">
                          {a.published_at ? new Date(a.published_at).toLocaleString('zh-CN') : ''}
                        </span>
                      </div>
                    </div>
                    {/* Bookmark button */}
                    <button
                      onClick={() => activeBookmark === a.id ? closeBookmarkPanel() : openBookmarkPanel(a.id)}
                      className={`shrink-0 mt-0.5 p-1 rounded hover:bg-bg transition-colors ${bookmarks[a.id] ? 'text-primary' : 'text-text-secondary'}`}
                      title={bookmarks[a.id] ? '已收藏' : '收藏'}
                    >
                      {bookmarks[a.id] ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
                    </button>
                  </div>

                  {/* Bookmark panel inline below article */}
                  {activeBookmark === a.id && (
                    <div className="mt-3 ml-7 p-3 bg-bg rounded-lg border border-border">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-medium">
                          {bookmarks[a.id] ? '编辑收藏' : '添加收藏'}
                        </span>
                        <button onClick={closeBookmarkPanel} className="text-text-secondary hover:text-text">
                          <X size={14} />
                        </button>
                      </div>
                      <textarea
                        value={bookmarkNote}
                        onChange={e => setBookmarkNote(e.target.value)}
                        placeholder="添加笔记（可选）..."
                        maxLength={2000}
                        rows={2}
                        className="w-full text-xs px-2 py-1.5 rounded border border-border resize-none mb-2"
                      />
                      <div className="flex items-center gap-1.5 mb-2">
                        <Tag size={12} className="text-text-secondary shrink-0" />
                        <input
                          value={bookmarkTags}
                          onChange={e => setBookmarkTags(e.target.value)}
                          placeholder="标签，逗号分隔（如: 美联储, 比特币）"
                          className="flex-1 text-xs px-2 py-1 rounded border border-border"
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => saveBookmark(a.id)}
                          disabled={bookmarkSaving}
                          className="px-3 py-1 bg-primary text-white text-xs rounded hover:bg-primary-dark disabled:opacity-50"
                        >
                          {bookmarkSaving ? '保存中...' : '保存'}
                        </button>
                        {bookmarks[a.id] && (
                          <button
                            onClick={() => removeBookmark(a.id)}
                            className="px-3 py-1 bg-danger text-white text-xs rounded hover:opacity-90"
                          >
                            取消收藏
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            {/* Pagination */}
            {data.pages > 1 && (
              <div className="flex items-center justify-center gap-2 p-4 border-t border-border">
                <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1} className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40">
                  上一页
                </button>
                <span className="text-sm text-text-secondary">
                  {data.page} / {data.pages}
                </span>
                <button onClick={() => setPage(p => Math.min(data.pages, p + 1))} disabled={page >= data.pages} className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40">
                  下一页
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
