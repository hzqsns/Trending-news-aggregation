import { useEffect, useState } from 'react'
import { CalendarDays, Plus, Trash2, Download, X, Clock } from 'lucide-react'
import { calendarApi } from '@/api'

interface CalendarEvent {
  id: number
  title: string
  event_type: 'economic' | 'earnings' | 'custom'
  event_date: string
  event_time: string | null
  description: string | null
  importance: 'high' | 'medium' | 'low'
  source: string | null
  meta: Record<string, unknown>
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  economic: '宏观经济',
  earnings: '财报',
  custom: '自定义',
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  economic: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  earnings: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  custom: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
}

const IMPORTANCE_DOT: Record<string, string> = {
  high: 'bg-red-500',
  medium: 'bg-yellow-400',
  low: 'bg-gray-400',
}

function getCountdown(eventDate: string): string {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(eventDate)
  target.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)
  if (diff === 0) return '今天'
  if (diff === 1) return '明天'
  if (diff === -1) return '昨天'
  if (diff > 0) return `${diff} 天后`
  return `${-diff} 天前`
}

function getCountdownClass(eventDate: string): string {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const target = new Date(eventDate)
  target.setHours(0, 0, 0, 0)
  const diff = Math.round((target.getTime() - today.getTime()) / 86400000)
  if (diff < 0) return 'text-text-secondary'
  if (diff === 0) return 'text-red-500 font-semibold'
  if (diff <= 3) return 'text-amber-500 font-medium'
  return 'text-text-secondary'
}

const FILTER_TYPES = [
  { key: '', label: '全部' },
  { key: 'economic', label: '📊 宏观经济' },
  { key: 'earnings', label: '💼 财报' },
  { key: 'custom', label: '📌 自定义' },
]

const DAY_RANGES = [
  { value: 30, label: '未来30天' },
  { value: 90, label: '未来3个月' },
  { value: 180, label: '未来6个月' },
]

interface AddEventForm {
  title: string
  event_type: string
  event_date: string
  event_time: string
  description: string
  importance: string
}

const defaultForm: AddEventForm = {
  title: '',
  event_type: 'custom',
  event_date: new Date().toISOString().slice(0, 10),
  event_time: '',
  description: '',
  importance: 'medium',
}

export default function Calendar() {
  const [events, setEvents] = useState<CalendarEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [days, setDays] = useState(90)
  const [seeding, setSeeding] = useState(false)
  const [seedResult, setSeedResult] = useState<string | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [addForm, setAddForm] = useState<AddEventForm>(defaultForm)
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const params: Record<string, unknown> = { days }
      if (filterType) params.event_type = filterType
      const resp = await calendarApi.list(params)
      setEvents(resp.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [filterType, days])

  const seedBuiltin = async () => {
    setSeeding(true)
    setSeedResult(null)
    try {
      const resp = await calendarApi.seed()
      setSeedResult(`已导入 ${resp.data.added} 条内置经济日历`)
      await load()
    } catch (e: any) {
      setSeedResult(`导入失败：${e.response?.data?.detail || e.message}`)
    } finally {
      setSeeding(false)
    }
  }

  const deleteEvent = async (id: number) => {
    try {
      await calendarApi.remove(id)
      setEvents((prev) => prev.filter((e) => e.id !== id))
    } catch (e) {
      console.error(e)
    }
  }

  const handleAdd = async () => {
    if (!addForm.title.trim() || !addForm.event_date) {
      setAddError('标题和日期为必填项')
      return
    }
    setAdding(true)
    setAddError(null)
    try {
      await calendarApi.create({
        title: addForm.title.trim(),
        event_type: addForm.event_type,
        event_date: addForm.event_date,
        event_time: addForm.event_time || undefined,
        description: addForm.description || undefined,
        importance: addForm.importance,
      })
      setShowAddModal(false)
      setAddForm(defaultForm)
      await load()
    } catch (e: any) {
      setAddError(e.response?.data?.detail || e.message)
    } finally {
      setAdding(false)
    }
  }

  // 按日期分组
  const grouped: Record<string, CalendarEvent[]> = {}
  for (const ev of events) {
    grouped[ev.event_date] = grouped[ev.event_date] || []
    grouped[ev.event_date].push(ev)
  }
  const sortedDates = Object.keys(grouped).sort()

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">金融日历</h2>
        <div className="flex gap-2">
          <button
            onClick={seedBuiltin}
            disabled={seeding}
            className="flex items-center gap-1.5 px-3 py-2 border border-border rounded-lg text-sm hover:bg-bg transition-colors disabled:opacity-50"
          >
            <Download size={15} />
            {seeding ? '导入中...' : '导入内置日历'}
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors"
          >
            <Plus size={15} />
            添加事件
          </button>
        </div>
      </div>

      {seedResult && (
        <div className="mb-4 p-3 bg-card border border-border rounded-lg text-sm text-text-secondary">
          {seedResult}
        </div>
      )}

      {/* 过滤器 */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex gap-1 bg-card rounded-xl p-1 border border-border">
          {FILTER_TYPES.map((ft) => (
            <button
              key={ft.key}
              onClick={() => setFilterType(ft.key)}
              className={`px-3 py-1.5 rounded-lg text-sm transition-colors whitespace-nowrap ${filterType === ft.key ? 'bg-primary text-white' : 'text-text-secondary hover:text-text'}`}
            >
              {ft.label}
            </button>
          ))}
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-1.5 rounded-lg border border-border text-sm bg-card"
        >
          {DAY_RANGES.map((r) => (
            <option key={r.value} value={r.value}>{r.label}</option>
          ))}
        </select>
      </div>

      {/* 事件列表 */}
      {loading ? (
        <div className="p-12 text-center text-text-secondary">加载中...</div>
      ) : sortedDates.length === 0 ? (
        <div className="bg-card rounded-xl border border-border p-12 text-center">
          <CalendarDays size={40} className="mx-auto mb-3 text-text-secondary opacity-40" />
          <p className="text-text-secondary text-sm">暂无日历事件</p>
          <p className="text-text-secondary text-xs mt-1">点击右上角「导入内置日历」获取2026年FOMC/CPI/NFP日期，或手动添加事件</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedDates.map((dateStr) => {
            const dayEvents = grouped[dateStr]
            const d = new Date(dateStr)
            const isPast = d < new Date(new Date().toDateString())
            return (
              <div key={dateStr} className={`bg-card rounded-xl border border-border overflow-hidden ${isPast ? 'opacity-60' : ''}`}>
                <div className="px-5 py-3 bg-bg border-b border-border flex items-center gap-3">
                  <CalendarDays size={15} className="text-text-secondary" />
                  <span className="text-sm font-semibold">
                    {d.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'short' })}
                  </span>
                  <span className={`text-xs ml-auto ${getCountdownClass(dateStr)}`}>
                    {getCountdown(dateStr)}
                  </span>
                </div>
                <div className="divide-y divide-border">
                  {dayEvents.map((ev) => (
                    <div key={ev.id} className="flex items-start gap-3 px-5 py-3.5">
                      <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${IMPORTANCE_DOT[ev.importance]}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${EVENT_TYPE_COLORS[ev.event_type]}`}>
                            {EVENT_TYPE_LABELS[ev.event_type]}
                          </span>
                          <span className="text-sm font-medium truncate">{ev.title}</span>
                        </div>
                        {ev.description && (
                          <p className="text-xs text-text-secondary mt-0.5 line-clamp-1">{ev.description}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-3 shrink-0">
                        {ev.event_time && (
                          <div className="flex items-center gap-1 text-xs text-text-secondary">
                            <Clock size={12} />
                            {ev.event_time} UTC
                          </div>
                        )}
                        <button
                          onClick={() => deleteEvent(ev.id)}
                          className="p-1 text-text-secondary hover:text-red-500 rounded transition-colors"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* 添加事件弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl border border-border w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className="font-semibold">添加日历事件</h3>
              <button onClick={() => { setShowAddModal(false); setAddForm(defaultForm); setAddError(null) }} className="text-text-secondary hover:text-text">
                <X size={18} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-text-secondary mb-1 block">标题 *</label>
                <input
                  type="text"
                  value={addForm.title}
                  onChange={(e) => setAddForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder="如：NVDA Q4 财报"
                  className="w-full px-3 py-2 rounded-lg border border-border text-sm"
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">类型</label>
                  <select
                    value={addForm.event_type}
                    onChange={(e) => setAddForm((f) => ({ ...f, event_type: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-border text-sm bg-card"
                  >
                    <option value="custom">自定义</option>
                    <option value="economic">宏观经济</option>
                    <option value="earnings">财报</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">重要性</label>
                  <select
                    value={addForm.importance}
                    onChange={(e) => setAddForm((f) => ({ ...f, importance: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-border text-sm bg-card"
                  >
                    <option value="high">🔴 高</option>
                    <option value="medium">🟡 中</option>
                    <option value="low">⚫ 低</option>
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">日期 *</label>
                  <input
                    type="date"
                    value={addForm.event_date}
                    onChange={(e) => setAddForm((f) => ({ ...f, event_date: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-border text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs font-medium text-text-secondary mb-1 block">时间（UTC，可选）</label>
                  <input
                    type="text"
                    value={addForm.event_time}
                    onChange={(e) => setAddForm((f) => ({ ...f, event_time: e.target.value }))}
                    placeholder="如：13:30"
                    className="w-full px-3 py-2 rounded-lg border border-border text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="text-xs font-medium text-text-secondary mb-1 block">描述（可选）</label>
                <textarea
                  value={addForm.description}
                  onChange={(e) => setAddForm((f) => ({ ...f, description: e.target.value }))}
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg border border-border text-sm resize-none"
                />
              </div>
              {addError && <p className="text-sm text-red-500">{addError}</p>}
            </div>
            <div className="flex justify-end gap-2 px-5 pb-5">
              <button
                onClick={() => { setShowAddModal(false); setAddForm(defaultForm); setAddError(null) }}
                className="px-4 py-2 rounded-lg border border-border text-sm hover:bg-bg transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleAdd}
                disabled={adding}
                className="px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                {adding ? '添加中...' : '添加'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
