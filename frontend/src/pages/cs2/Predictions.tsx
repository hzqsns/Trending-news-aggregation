import { useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { cs2Api, type Cs2Prediction } from '@/api/cs2'
import { Loading, Empty, useToast } from '@/components/ui'
import { PredictionCard } from '@/components/cs2/PredictionCard'

export default function Cs2Predictions() {
  const navigate = useNavigate()
  const [predictions, setPredictions] = useState<Cs2Prediction[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [period, setPeriod] = useState<'7d' | '14d' | '30d'>('7d')
  const [direction, setDirection] = useState<'all' | 'bullish' | 'bearish' | 'neutral'>('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const { data } = await cs2Api.predictions({ period, direction })
      setPredictions(data.items)
    } finally {
      setLoading(false)
    }
  }, [period, direction])

  useEffect(() => { load() }, [load])

  const toast = useToast()

  const handleGenerate = async () => {
    setGenerating(true)
    try {
      const { data } = await cs2Api.generateAllPredictions(period, 20)
      toast.success(`预测生成完成：成功 ${data.generated} 个，失败 ${data.failed} 个`)
      if (data.generated > 0) {
        await load()
      }
    } catch {
      toast.error('预测生成失败，请检查 AI 配置')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">AI 预测</h1>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-amber-600 text-white hover:bg-amber-500 disabled:opacity-50 transition-colors"
        >
          <Sparkles size={14} className={generating ? 'animate-pulse' : ''} />
          {generating ? '生成中...' : '手动生成预测'}
        </button>
      </div>

      <div className="flex flex-wrap gap-2">
        <div className="flex gap-1 bg-card rounded-lg p-1 border border-border">
          {(['7d', '14d', '30d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1 text-xs rounded ${period === p ? 'bg-amber-600 text-white' : 'text-text-secondary'}`}
            >
              {p}
            </button>
          ))}
        </div>
        <div className="flex gap-1 bg-card rounded-lg p-1 border border-border">
          {(['all', 'bullish', 'bearish', 'neutral'] as const).map((d) => (
            <button
              key={d}
              onClick={() => setDirection(d)}
              className={`px-3 py-1 text-xs rounded ${direction === d ? 'bg-amber-600 text-white' : 'text-text-secondary'}`}
            >
              {d === 'all' ? '全部' : d === 'bullish' ? '看多' : d === 'bearish' ? '看空' : '中性'}
            </button>
          ))}
        </div>
      </div>

      {loading ? <Loading /> : predictions.length === 0 ? (
        <Empty>暂无预测数据，等待每日 09:00 自动生成</Empty>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {predictions.map((p) => (
            <PredictionCard
              key={p.id}
              prediction={p}
              onClick={() => navigate(`/cs2/item/${p.item_id}`)}
            />
          ))}
        </div>
      )}
    </div>
  )
}
