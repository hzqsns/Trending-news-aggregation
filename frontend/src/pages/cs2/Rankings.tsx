import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { cs2Api, type Cs2RankingItem } from '@/api/cs2'
import { Card, Loading, Empty, Input, Select } from '@/components/ui'
import { RarityBadge } from '@/components/cs2/RarityBadge'

export default function Cs2Rankings() {
  const [items, setItems] = useState<Cs2RankingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('24h')
  const [direction, setDirection] = useState<'gainers' | 'losers'>('gainers')
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string | number> = {
        period, direction, page, page_size: 20,
      }
      if (category) params.category = category
      if (search) params.search = search
      const { data } = await cs2Api.rankings(params)
      setItems(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [period, direction, category, search, page])

  useEffect(() => { load() }, [load])

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold">涨跌榜</h1>

      <Card className="p-4">
        <div className="flex flex-wrap gap-2 items-center">
          <div className="flex gap-1 bg-bg rounded-lg p-1">
            {(['24h', '7d', '30d'] as const).map((p) => (
              <button
                key={p}
                onClick={() => { setPeriod(p); setPage(1) }}
                className={`px-3 py-1 text-xs rounded ${period === p ? 'bg-amber-600 text-white' : 'text-text-secondary'}`}
              >
                {p}
              </button>
            ))}
          </div>
          <div className="flex gap-1 bg-bg rounded-lg p-1">
            <button
              onClick={() => { setDirection('gainers'); setPage(1) }}
              className={`px-3 py-1 text-xs rounded ${direction === 'gainers' ? 'bg-green-600 text-white' : 'text-text-secondary'}`}
            >
              涨幅榜
            </button>
            <button
              onClick={() => { setDirection('losers'); setPage(1) }}
              className={`px-3 py-1 text-xs rounded ${direction === 'losers' ? 'bg-red-600 text-white' : 'text-text-secondary'}`}
            >
              跌幅榜
            </button>
          </div>
          <Select value={category} onChange={(e) => { setCategory(e.target.value); setPage(1) }} className="text-xs">
            <option value="">全部品类</option>
            <option value="knife">刀具</option>
            <option value="gloves">手套</option>
            <option value="rifle">步枪</option>
            <option value="pistol">手枪</option>
            <option value="smg">冲锋枪</option>
            <option value="shotgun">霰弹枪</option>
            <option value="mg">机枪</option>
            <option value="sticker">贴纸</option>
            <option value="case">箱子</option>
          </Select>
          <Input
            type="text"
            placeholder="搜索..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="text-xs w-40"
          />
        </div>
      </Card>

      {loading ? <Loading /> : items.length === 0 ? <Empty>暂无排行数据</Empty> : (
        <Card className="p-0 overflow-hidden">
          <div className="divide-y divide-border">
            {items.map((item, idx) => (
              <Link
                key={item.id}
                to={`/cs2/item/${item.id}`}
                className="flex items-center gap-3 p-4 hover:bg-bg/50 transition-colors"
              >
                <span className="text-xs font-bold text-text-secondary w-6 text-center">
                  {(page - 1) * 20 + idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate">{item.name}</span>
                    <RarityBadge rarity={item.rarity} />
                  </div>
                  <div className="text-xs text-text-secondary mt-0.5">{item.category}</div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold">¥{item.current_price.toFixed(2)}</div>
                  <div className={`text-xs ${item.change_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </Card>
      )}

      {total > 20 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40"
          >
            上一页
          </button>
          <span className="text-sm text-text-secondary">第 {page} 页 / 共 {Math.ceil(total / 20)} 页</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={items.length < 20}
            className="px-3 py-1.5 text-sm rounded border border-border hover:bg-bg disabled:opacity-40"
          >
            下一页
          </button>
        </div>
      )}
    </div>
  )
}
