import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Package, TrendingUp, Activity, Flame, RefreshCw } from 'lucide-react'
import { cs2Api } from '@/api/cs2'
import { Card, CardHeader, CardTitle, Loading, useToast } from '@/components/ui'
import { MarketStatCard } from '@/components/cs2/MarketStatCard'
import { RarityBadge } from '@/components/cs2/RarityBadge'

interface Overview {
  period: string
  total_items: number
  total_market_cap: number
  total_volume: number
  gainers: number
  losers: number
  sentiment_index: number
}

interface HotItem {
  id: number
  display_name: string
  category: string
  rarity: string | null
  image_url: string | null
  current_price: number
  volume_24h: number
}

export default function Cs2Dashboard() {
  const [overview, setOverview] = useState<Overview | null>(null)
  const [hotItems, setHotItems] = useState<HotItem[]>([])
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('24h')

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const [ovRes, hotRes] = await Promise.all([
          cs2Api.marketOverview(period),
          cs2Api.hotItems(10),
        ])
        if (cancelled) return
        setOverview(ovRes.data)
        setHotItems(hotRes.data.items)
      } catch {
        /* ignore */
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [period])

  const [refreshing, setRefreshing] = useState(false)
  const toast = useToast()

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await cs2Api.marketRefresh()
      const [ovRes, hotRes] = await Promise.all([
        cs2Api.marketOverview(period),
        cs2Api.hotItems(10),
      ])
      setOverview(ovRes.data)
      setHotItems(hotRes.data.items)
      toast.success('行情刷新完成')
    } catch {
      toast.error('行情刷新失败，请稍后重试')
    } finally {
      setRefreshing(false)
    }
  }

  if (loading && !overview) return <Loading />

  const sentiment = overview?.sentiment_index ?? 50
  const sentimentLabel = sentiment >= 70 ? '贪婪' : sentiment >= 50 ? '中性' : sentiment >= 30 ? '谨慎' : '恐慌'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">CS2 市场总览</h1>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 rounded-lg hover:bg-bg text-text-secondary hover:text-text transition-colors disabled:opacity-50"
            title="手动刷新行情（从 Steam 拉取最新价格）"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} />
          </button>
        </div>
        <div className="flex gap-1 bg-card rounded-lg p-1 border border-border">
          {(['24h', '7d', '30d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 text-xs rounded transition-colors ${
                period === p ? 'bg-amber-600 text-white' : 'text-text-secondary hover:text-text'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MarketStatCard
          label="追踪饰品数"
          value={overview?.total_items ?? 0}
          icon={Package}
          iconColor="text-amber-500"
        />
        <MarketStatCard
          label="总市值 (CNY)"
          value={`¥${(overview?.total_market_cap ?? 0).toLocaleString()}`}
          icon={TrendingUp}
          iconColor="text-blue-500"
        />
        <MarketStatCard
          label={`${period} 成交量`}
          value={(overview?.total_volume ?? 0).toLocaleString()}
          icon={Activity}
          iconColor="text-green-500"
        />
        <MarketStatCard
          label="市场情绪"
          value={`${sentiment} ${sentimentLabel}`}
          icon={Flame}
          iconColor={sentiment >= 50 ? 'text-green-500' : 'text-red-500'}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>涨跌家数 ({period})</CardTitle>
        </CardHeader>
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-green-500 font-semibold">↑ {overview?.gainers ?? 0}</span>
            <span className="text-text-secondary ml-1">上涨</span>
          </div>
          <div>
            <span className="text-red-500 font-semibold">↓ {overview?.losers ?? 0}</span>
            <span className="text-text-secondary ml-1">下跌</span>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>热门饰品 Top 10</CardTitle>
        </CardHeader>
        {hotItems.length === 0 ? (
          <p className="text-sm text-text-secondary">暂无数据，等待首次采集</p>
        ) : (
          <div className="divide-y divide-border -mx-6">
            {hotItems.map((item, idx) => (
              <Link
                key={item.id}
                to={`/cs2/item/${item.id}`}
                className="flex items-center gap-3 px-6 py-3 hover:bg-bg/50 transition-colors"
              >
                <span className="text-xs font-bold text-text-secondary w-5">{idx + 1}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{item.display_name || 'Unknown'}</span>
                    <RarityBadge rarity={item.rarity} />
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">
                    {item.category} · 成交量 {item.volume_24h.toLocaleString()}
                  </div>
                </div>
                <div className="text-sm font-bold text-amber-500">¥{item.current_price?.toFixed(2) ?? '—'}</div>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
