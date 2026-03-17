import { useEffect, useState } from 'react'
import { Search, Bookmark, ExternalLink, Tag, Edit2, Trash2 } from 'lucide-react'
import { bookmarksApi } from '@/api'

interface BookmarkItem {
  id: number
  article_id: number
  note: string | null
  tags: string[]
  created_at: string
  article: {
    id: number
    title: string
    url: string
    source: string
    category: string
    published_at: string | null
  }
}

export default function Bookmarks() {
  const [items, setItems] = useState<BookmarkItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pages, setPages] = useState(0)
  const [loading, setLoading] = useState(true)
  const [allTags, setAllTags] = useState<string[]>([])
  const [activeTag, setActiveTag] = useState<string>('')
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editNote, setEditNote] = useState('')
  const [editTags, setEditTags] = useState('')
  const [saving, setSaving] = useState(false)

  const loadBookmarks = async (p = page, tag = activeTag, q = search) => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { page: p, page_size: 20 }
      if (tag) params.tag = tag
      if (q) params.search = q
      const resp = await bookmarksApi.list(params)
      setItems(resp.data.items)
      setTotal(resp.data.total)
      setPages(resp.data.pages)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const loadTags = async () => {
    try {
      const resp = await bookmarksApi.tags()
      setAllTags(resp.data)
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    loadTags()
  }, [])

  useEffect(() => {
    loadBookmarks(page, activeTag, search)
  }, [page, activeTag, search])

  const handleTagFilter = (tag: string) => {
    setActiveTag(tag)
    setPage(1)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearch(searchInput)
    setPage(1)
  }

  const startEdit = (item: BookmarkItem) => {
    setEditingId(item.article_id)
    setEditNote(item.note ?? '')
    setEditTags(item.tags.join(', '))
  }

  const cancelEdit = () => setEditingId(null)

  const saveEdit = async (articleId: number) => {
    setSaving(true)
    const tags = editTags.split(',').map(t => t.trim()).filter(Boolean)
    try {
      await bookmarksApi.update(articleId, editNote || null, tags)
      setEditingId(null)
      await loadBookmarks()
      await loadTags()
    } catch (e) {
      console.error(e)
    } finally {
      setSaving(false)
    }
  }

  const removeBookmark = async (articleId: number) => {
    if (!confirm('确认取消收藏？')) return
    try {
      await bookmarksApi.remove(articleId)
      await loadBookmarks()
      await loadTags()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">收藏夹</h2>
        <span className="text-sm text-text-secondary">共 {total} 篇</span>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-4">
        <div className="relative max-w-md">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="搜索收藏文章..."
            className="w-full pl-9 pr-4 py-2 rounded-lg border border-border text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>
      </form>

      {/* Tag filter chips */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          <button
            onClick={() => handleTagFilter('')}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              activeTag === '' ? 'bg-primary text-white' : 'bg-bg text-text-secondary hover:bg-border'
            }`}
          >
            全部
          </button>
          {allTags.map(tag => (
            <button
              key={tag}
              onClick={() => handleTagFilter(tag)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                activeTag === tag ? 'bg-primary text-white' : 'bg-bg text-text-secondary hover:bg-border'
              }`}
            >
              #{tag}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      {loading ? (
        <div className="p-8 text-center text-text-secondary">加载中...</div>
      ) : items.length === 0 ? (
        <div className="bg-card rounded-xl p-12 text-center border border-border">
          <Bookmark size={48} className="mx-auto text-text-secondary/30 mb-4" />
          <p className="text-text-secondary font-medium">暂无收藏</p>
          <p className="text-xs text-text-secondary mt-1">在新闻流中点击书签图标收藏感兴趣的文章</p>
        </div>
      ) : (
        <>
          <div className="bg-card rounded-xl border border-border divide-y divide-border">
            {items.map(item => (
              <div key={item.article_id} className="p-4">
                <div className="flex items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <a
                      href={item.article.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm font-medium hover:text-primary flex items-center gap-1"
                    >
                      <span className="truncate">{item.article.title}</span>
                      <ExternalLink size={12} className="shrink-0 text-text-secondary" />
                    </a>
                    <div className="flex items-center gap-2 mt-1 flex-wrap">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-bg">{item.article.source}</span>
                      {item.article.published_at && (
                        <span className="text-xs text-text-secondary">
                          {new Date(item.article.published_at).toLocaleString('zh-CN')}
                        </span>
                      )}
                    </div>
                    {item.note && (
                      <p className="mt-1.5 text-xs text-text-secondary italic line-clamp-2">"{item.note}"</p>
                    )}
                    {item.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {item.tags.map(tag => (
                          <span key={tag} className="text-xs text-primary">#{tag}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => editingId === item.article_id ? cancelEdit() : startEdit(item)}
                      className="p-1.5 rounded hover:bg-bg text-text-secondary hover:text-text transition-colors"
                      title="编辑"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      onClick={() => removeBookmark(item.article_id)}
                      className="p-1.5 rounded hover:bg-bg text-text-secondary hover:text-danger transition-colors"
                      title="取消收藏"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>

                {/* Inline edit */}
                {editingId === item.article_id && (
                  <div className="mt-3 p-3 bg-bg rounded-lg border border-border">
                    <textarea
                      value={editNote}
                      onChange={e => setEditNote(e.target.value)}
                      placeholder="笔记..."
                      maxLength={2000}
                      rows={2}
                      className="w-full text-xs px-2 py-1.5 rounded border border-border resize-none mb-2"
                    />
                    <div className="flex items-center gap-1.5 mb-2">
                      <Tag size={12} className="text-text-secondary shrink-0" />
                      <input
                        value={editTags}
                        onChange={e => setEditTags(e.target.value)}
                        placeholder="标签，逗号分隔"
                        className="flex-1 text-xs px-2 py-1 rounded border border-border"
                      />
                    </div>
                    <div className="flex gap-2">
                      <button
                        onClick={() => saveEdit(item.article_id)}
                        disabled={saving}
                        className="px-3 py-1 bg-primary text-white text-xs rounded hover:bg-primary-dark disabled:opacity-50"
                      >
                        {saving ? '保存中...' : '保存'}
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="px-3 py-1 text-xs rounded border border-border hover:bg-bg"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Pagination */}
          {pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40"
              >
                上一页
              </button>
              <span className="text-sm text-text-secondary">{page} / {pages}</span>
              <button
                onClick={() => setPage(p => Math.min(pages, p + 1))}
                disabled={page >= pages}
                className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40"
              >
                下一页
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
