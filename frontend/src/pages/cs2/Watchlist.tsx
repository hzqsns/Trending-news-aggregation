import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { cs2Api } from '@/api/cs2'
import { Card, CardHeader, CardTitle, Loading, Empty, useToast } from '@/components/ui'

interface WatchItem {
  id: number
  item_id: number
  item_name: string
  image_url: string | null
  target_price: number | null
  alert_direction: string | null
  current_price: number | null
  triggered: boolean
  created_at: string | null
}

export default function Cs2Watchlist() {
  const [watches, setWatches] = useState<WatchItem[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const r = await cs2Api.watchlist()
      setWatches(r.data.items)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const r = await cs2Api.watchlist()
        if (!cancelled) setWatches(r.data.items)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [])

  const toast = useToast()

  const handleDelete = async (watchId: number) => {
    if (!window.confirm('确定要移除这个自选吗？')) return
    try {
      await cs2Api.deleteWatch(watchId)
      toast.success('已从自选中移除')
      load()
    } catch {
      toast.error('移除失败')
    }
  }

  if (loading) return <Loading />

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">自选监控</h1>

      <Card>
        <CardHeader>
          <CardTitle>我的自选 ({watches.length})</CardTitle>
        </CardHeader>
        {watches.length === 0 ? (
          <Empty>暂无自选饰品，从 <Link to="/cs2/rankings" className="text-amber-500 hover:underline">涨跌榜</Link> 添加</Empty>
        ) : (
          <div className="divide-y divide-border -mx-6">
            {watches.map((w) => {
              const distance = w.current_price && w.target_price
                ? ((w.target_price - w.current_price) / w.current_price * 100).toFixed(2)
                : null
              return (
                <div key={w.id} className="flex items-center gap-3 px-6 py-3">
                  <Link to={`/cs2/item/${w.item_id}`} className="flex-1 min-w-0 hover:underline">
                    <div className="text-sm font-medium truncate">{w.item_name}</div>
                    <div className="text-xs text-text-secondary mt-0.5">
                      目标价 {w.target_price ? `¥${w.target_price.toFixed(2)}` : '—'}
                      {w.alert_direction && ` (${w.alert_direction === 'above' ? '涨到' : '跌到'})`}
                    </div>
                  </Link>
                  <div className="text-right">
                    <div className="text-sm font-bold text-amber-500">
                      {w.current_price ? `¥${w.current_price.toFixed(2)}` : '—'}
                    </div>
                    {distance && (
                      <div className="text-xs text-text-secondary">
                        距 {distance}%
                      </div>
                    )}
                  </div>
                  {w.triggered && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-green-600/20 text-green-500">已触发</span>
                  )}
                  <button
                    onClick={() => handleDelete(w.id)}
                    className="text-text-secondary hover:text-red-500 transition-colors"
                    title="移除"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
