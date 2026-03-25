import { useEffect, useState } from 'react'
import { BookOpen, Plus, Trash2, ChevronDown, ChevronUp, Search, RefreshCw } from 'lucide-react'
import { historicalEventsApi } from '@/api'

interface KeyMetric {
  label: string
  value: string
}

interface HistoricalEvent {
  id: number
  title: string
  category: string
  date_range: string
  market_impact: 'bullish' | 'bearish' | 'mixed'
  description: string | null
  key_metrics: KeyMetric[] | null
  is_builtin: boolean
  created_at: string
}

const CATEGORIES = [
  { key: '', label: '全部' },
  { key: 'financial_crisis', label: '金融危机' },
  { key: 'monetary_policy', label: '货币政策' },
  { key: 'pandemic', label: '疫情' },
  { key: 'tech_bubble', label: '科技泡沫' },
  { key: 'geopolitics', label: '地缘政治' },
]

const IMPACT_COLORS: Record<string, string> = {
  bullish: 'text-success bg-success/10 border-success/20',
  bearish: 'text-danger bg-danger/10 border-danger/20',
  mixed: 'text-text-secondary bg-bg border-border',
}

const IMPACT_LABELS: Record<string, string> = {
  bullish: '利多',
  bearish: '利空',
  mixed: '中性',
}

const CATEGORY_LABELS: Record<string, string> = {
  financial_crisis: '金融危机',
  monetary_policy: '货币政策',
  pandemic: '疫情',
  tech_bubble: '科技泡沫',
  geopolitics: '地缘政治',
}

interface AddEventModalProps {
  onClose: () => void
  onSave: () => void
}

function AddEventModal({ onClose, onSave }: AddEventModalProps) {
  const [form, setForm] = useState({
    title: '',
    category: 'financial_crisis',
    date_range: '',
    market_impact: 'mixed' as 'bullish' | 'bearish' | 'mixed',
    description: '',
  })
  const [metrics, setMetrics] = useState<KeyMetric[]>([{ label: '', value: '' }])
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const addMetric = () => setMetrics((m) => [...m, { label: '', value: '' }])
  const removeMetric = (i: number) => setMetrics((m) => m.filter((_, idx) => idx !== i))
  const updateMetric = (i: number, field: 'label' | 'value', val: string) => {
    setMetrics((m) => m.map((item, idx) => idx === i ? { ...item, [field]: val } : item))
  }

  const handleSubmit = async () => {
    if (!form.title.trim() || !form.date_range.trim()) {
      setError('标题和时间范围为必填项')
      return
    }
    setSaving(true)
    setError('')
    try {
      const validMetrics = metrics.filter((m) => m.label.trim() && m.value.trim())
      await historicalEventsApi.create({
        ...form,
        key_metrics: validMetrics.length > 0 ? validMetrics : undefined,
      })
      onSave()
    } catch {
      setError('保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-card rounded-xl border border-border w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto">
        <h3 className="text-base font-semibold mb-4">新增历史事件</h3>

        <div className="space-y-3">
          <div>
            <label className="text-xs text-text-secondary mb-1 block">标题 *</label>
            <input
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="事件标题"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-text-secondary mb-1 block">分类</label>
              <select
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
                value={form.category}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {CATEGORIES.filter((c) => c.key).map((c) => (
                  <option key={c.key} value={c.key}>{c.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-text-secondary mb-1 block">市场影响</label>
              <select
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
                value={form.market_impact}
                onChange={(e) => setForm({ ...form, market_impact: e.target.value as 'bullish' | 'bearish' | 'mixed' })}
              >
                <option value="bullish">利多</option>
                <option value="bearish">利空</option>
                <option value="mixed">中性</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs text-text-secondary mb-1 block">时间范围 * (如: 2008-09 ~ 2009-06)</label>
            <input
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary"
              value={form.date_range}
              onChange={(e) => setForm({ ...form, date_range: e.target.value })}
              placeholder="YYYY-MM ~ YYYY-MM"
            />
          </div>

          <div>
            <label className="text-xs text-text-secondary mb-1 block">描述</label>
            <textarea
              className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-primary resize-none"
              rows={3}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="事件详细描述..."
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-text-secondary">关键指标</label>
              <button onClick={addMetric} className="text-xs text-primary hover:underline">+ 添加</button>
            </div>
            {metrics.map((m, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  className="flex-1 bg-bg border border-border rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-primary"
                  value={m.label}
                  onChange={(e) => updateMetric(i, 'label', e.target.value)}
                  placeholder="指标名称"
                />
                <input
                  className="flex-1 bg-bg border border-border rounded-lg px-2 py-1.5 text-xs focus:outline-none focus:border-primary"
                  value={m.value}
                  onChange={(e) => updateMetric(i, 'value', e.target.value)}
                  placeholder="指标值"
                />
                {metrics.length > 1 && (
                  <button onClick={() => removeMetric(i)} className="text-text-secondary hover:text-danger px-1">×</button>
                )}
              </div>
            ))}
          </div>
        </div>

        {error && <p className="text-danger text-xs mt-2">{error}</p>}

        <div className="flex gap-2 mt-4">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-border rounded-lg text-sm hover:bg-bg transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={saving}
            className="flex-1 px-4 py-2 bg-primary text-white rounded-lg text-sm hover:opacity-90 transition-opacity disabled:opacity-50"
          >
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </div>
    </div>
  )
}

function EventCard({ event, onDelete }: { event: HistoricalEvent; onDelete: () => void }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="bg-card rounded-xl border border-border overflow-hidden">
      <div
        className="p-4 cursor-pointer hover:bg-bg/50 transition-colors"
        onClick={() => setExpanded((e) => !e)}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`text-xs px-2 py-0.5 rounded border ${IMPACT_COLORS[event.market_impact]}`}>
                {IMPACT_LABELS[event.market_impact]}
              </span>
              <span className="text-xs text-text-secondary bg-bg px-2 py-0.5 rounded border border-border">
                {CATEGORY_LABELS[event.category] || event.category}
              </span>
            </div>
            <h3 className="font-semibold text-sm">{event.title}</h3>
            <p className="text-xs text-text-secondary mt-0.5">{event.date_range}</p>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {!event.is_builtin && (
              <button
                onClick={(e) => { e.stopPropagation(); onDelete() }}
                className="p-1 text-text-secondary hover:text-danger transition-colors"
              >
                <Trash2 size={14} />
              </button>
            )}
            {expanded
              ? <ChevronUp size={14} className="text-text-secondary" />
              : <ChevronDown size={14} className="text-text-secondary" />
            }
          </div>
        </div>
      </div>

      {expanded && (event.description || (event.key_metrics && event.key_metrics.length > 0)) && (
        <div className="px-4 pb-4 border-t border-border pt-3 space-y-3">
          {event.description && (
            <p className="text-sm text-text-secondary leading-relaxed">{event.description}</p>
          )}
          {event.key_metrics && event.key_metrics.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {event.key_metrics.map((m, i) => (
                <div key={i} className="bg-bg rounded-lg p-2.5 border border-border">
                  <p className="text-xs text-text-secondary">{m.label}</p>
                  <p className="text-sm font-semibold mt-0.5">{m.value}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function HistoricalEvents() {
  const [events, setEvents] = useState<HistoricalEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [showModal, setShowModal] = useState(false)
  const [seeding, setSeeding] = useState(false)

  const load = async () => {
    try {
      const resp = await historicalEventsApi.list({ category: category || undefined, search: search || undefined })
      setEvents(resp.data)
    } catch (e) {
      console.error('Failed to load historical events', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [category, search])

  const handleDelete = async (id: number) => {
    if (!confirm('确认删除该事件？')) return
    try {
      await historicalEventsApi.remove(id)
      setEvents((prev) => prev.filter((e) => e.id !== id))
    } catch {
      alert('删除失败')
    }
  }

  const handleSeed = async () => {
    setSeeding(true)
    try {
      await historicalEventsApi.seed()
      await load()
    } catch {
      alert('导入失败')
    } finally {
      setSeeding(false)
    }
  }

  if (loading) {
    return (
      <div>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold">历史事件库</h2>
        </div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="bg-card rounded-xl border border-border p-4 animate-pulse h-20" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">历史事件库</h2>
        <div className="flex gap-2">
          <button
            onClick={handleSeed}
            disabled={seeding}
            className="flex items-center gap-1.5 px-3 py-2 border border-border rounded-lg text-sm hover:bg-bg transition-colors disabled:opacity-50"
          >
            <RefreshCw size={14} className={seeding ? 'animate-spin' : ''} />
            {seeding ? '导入中...' : '导入内置'}
          </button>
          <button
            onClick={() => setShowModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 bg-primary text-white rounded-lg text-sm hover:opacity-90 transition-opacity"
          >
            <Plus size={14} />
            新增事件
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-secondary" />
        <input
          className="w-full bg-card border border-border rounded-lg pl-8 pr-4 py-2 text-sm focus:outline-none focus:border-primary"
          placeholder="搜索标题或描述..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {/* Category Chips */}
      <div className="flex gap-2 flex-wrap mb-6">
        {CATEGORIES.map((c) => (
          <button
            key={c.key}
            onClick={() => setCategory(c.key)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              category === c.key
                ? 'bg-primary text-white'
                : 'bg-card border border-border text-text-secondary hover:text-text'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {events.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <BookOpen size={40} className="mx-auto mb-3 text-text-secondary opacity-40" />
          <p className="text-text-secondary text-sm">暂无历史事件</p>
          <p className="text-text-secondary text-xs mt-1">点击「导入内置」加载预设历史事件，或「新增事件」手动添加</p>
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((event) => (
            <EventCard
              key={event.id}
              event={event}
              onDelete={() => handleDelete(event.id)}
            />
          ))}
        </div>
      )}

      {showModal && (
        <AddEventModal
          onClose={() => setShowModal(false)}
          onSave={() => { setShowModal(false); load() }}
        />
      )}
    </div>
  )
}
