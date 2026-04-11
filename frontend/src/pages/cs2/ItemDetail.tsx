import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { cs2Api, type Cs2Prediction } from '@/api/cs2'
import { Card, CardHeader, CardTitle, Loading, Empty, useToast } from '@/components/ui'
import { RarityBadge } from '@/components/cs2/RarityBadge'
import { KlineChart } from '@/components/cs2/KlineChart'
import { PredictionCard } from '@/components/cs2/PredictionCard'

interface ItemDetail {
  id: number
  display_name: string
  category: string
  subcategory: string | null
  rarity: string | null
  image_url: string | null
  current_price: number | null
  volume_24h: number
  prediction: Cs2Prediction | null
}

interface KlinePoint {
  time: string
  price: number
  volume: number
}

export default function Cs2ItemDetail() {
  const { id } = useParams<{ id: string }>()
  const [item, setItem] = useState<ItemDetail | null>(null)
  const [kline, setKline] = useState<KlinePoint[]>([])
  const [period, setPeriod] = useState<'1d' | '7d' | '30d' | '90d'>('7d')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const itemId = Number(id)
    let cancelled = false
    const run = async () => {
      try {
        const [itemRes, klineRes] = await Promise.all([
          cs2Api.itemDetail(itemId),
          cs2Api.itemKline(itemId, period),
        ])
        if (cancelled) return
        setItem(itemRes.data)
        setKline(klineRes.data.points)
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [id, period])

  const toast = useToast()
  const [regenerating, setRegenerating] = useState(false)

  if (loading && !item) return <Loading />
  if (!item) return <Empty>饰品不存在</Empty>

  return (
    <div className="space-y-6">
      <Link to="/cs2/rankings" className="inline-flex items-center gap-1 text-sm text-text-secondary hover:text-text">
        <ArrowLeft size={14} /> 返回
      </Link>

      <Card>
        <div className="flex items-start gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h1 className="text-xl font-bold">{item.display_name}</h1>
              <RarityBadge rarity={item.rarity} />
            </div>
            <div className="text-sm text-text-secondary">
              {item.category} {item.subcategory ? `· ${item.subcategory}` : ''}
            </div>
            <div className="mt-4">
              <div className="text-3xl font-bold text-amber-500">
                {item.current_price !== null ? `¥${item.current_price.toFixed(2)}` : '—'}
              </div>
              <div className="text-xs text-text-secondary mt-1">
                24h 成交量：{item.volume_24h.toLocaleString()}
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>价格走势</CardTitle>
          <div className="flex gap-1">
            {(['1d', '7d', '30d', '90d'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-2.5 py-1 text-xs rounded ${period === p ? 'bg-amber-600 text-white' : 'bg-bg text-text-secondary'}`}
              >
                {p}
              </button>
            ))}
          </div>
        </CardHeader>
        <KlineChart data={kline} />
      </Card>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold">AI 预测</h2>
          <button
            disabled={regenerating}
            onClick={async () => {
              if (!id) return
              setRegenerating(true)
              try {
                await cs2Api.regeneratePrediction(Number(id), '7d')
                const r = await cs2Api.itemDetail(Number(id))
                setItem(r.data)
                toast.success('预测已更新')
              } catch {
                toast.error('预测生成失败（数据不足或 AI 配置有误）')
              } finally {
                setRegenerating(false)
              }
            }}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-lg bg-amber-600/10 text-amber-600 hover:bg-amber-600/20 disabled:opacity-50 transition-colors"
          >
            <RefreshCw size={12} className={regenerating ? 'animate-spin' : ''} />
            {regenerating ? '生成中...' : '刷新预测'}
          </button>
        </div>
        {item.prediction ? (
          <PredictionCard prediction={item.prediction} />
        ) : (
          <p className="text-sm text-text-secondary p-4 bg-card rounded-xl border border-border">
            暂无预测数据，点击"刷新预测"手动生成
          </p>
        )}
      </div>
    </div>
  )
}
