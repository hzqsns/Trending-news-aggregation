import { useEffect, useState } from 'react'
import { cs2Api } from '@/api/cs2'
import { Card, CardHeader, CardTitle, Loading, Empty } from '@/components/ui'

interface Category {
  id: string
  name: string
  item_count: number
}

const CATEGORY_LABELS: Record<string, string> = {
  knife: '刀具',
  gloves: '手套',
  rifle: '步枪',
  pistol: '手枪',
  smg: '冲锋枪',
  shotgun: '霰弹枪',
  mg: '机枪',
  sticker: '贴纸',
  case: '箱子',
}

export default function Cs2Categories() {
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    cs2Api.categories()
      .then((r) => {
        setCategories(r.data.categories)
        if (r.data.categories.length > 0) setSelected(r.data.categories[0].id)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading />
  if (categories.length === 0) return <Empty>暂无品类数据</Empty>

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-bold">品类分析</h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {categories.map((cat) => (
          <Card
            key={cat.id}
            onClick={() => setSelected(cat.id)}
            className={`cursor-pointer transition-all ${
              selected === cat.id ? 'border-amber-500 shadow-lg' : 'hover:border-amber-500/40'
            }`}
          >
            <div className="text-sm text-text-secondary">{CATEGORY_LABELS[cat.id] ?? cat.name}</div>
            <div className="text-2xl font-bold mt-1">{cat.item_count}</div>
            <div className="text-xs text-text-secondary mt-1">个追踪饰品</div>
          </Card>
        ))}
      </div>

      {selected && (
        <Card>
          <CardHeader>
            <CardTitle>{CATEGORY_LABELS[selected] ?? selected} — 详细分析</CardTitle>
          </CardHeader>
          <p className="text-sm text-text-secondary">
            走势数据将在首次采集完成后显示。选中品类：<strong>{selected}</strong>
          </p>
        </Card>
      )}
    </div>
  )
}
