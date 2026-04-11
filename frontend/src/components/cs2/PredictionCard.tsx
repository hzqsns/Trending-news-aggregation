import { Card, Badge } from '@/components/ui'
import { ProbabilityBar } from './ProbabilityBar'
import type { Cs2Prediction } from '@/api/cs2'

interface Props {
  prediction: Cs2Prediction
  onClick?: () => void
}

export function PredictionCard({ prediction, onClick }: Props) {
  const { direction, up_prob, flat_prob, down_prob, reasoning, factors, item_name, predicted_price } = prediction

  const dirColor = direction === 'bullish' ? 'success' : direction === 'bearish' ? 'danger' : 'default'
  const dirLabel = direction === 'bullish' ? '看多' : direction === 'bearish' ? '看空' : '中性'

  return (
    <Card
      className={`${onClick ? 'cursor-pointer hover:border-amber-500/40 transition-colors' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold truncate">{item_name || `Item #${prediction.item_id}`}</h3>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant={dirColor}>{dirLabel}</Badge>
            <span className="text-xs text-text-secondary">{prediction.period} 预测</span>
          </div>
        </div>
        {predicted_price !== null && (
          <div className="text-right">
            <div className="text-xs text-text-secondary">目标价</div>
            <div className="text-sm font-bold text-amber-500">¥{predicted_price.toFixed(2)}</div>
          </div>
        )}
      </div>

      <ProbabilityBar up={up_prob} flat={flat_prob} down={down_prob} />

      {reasoning && (
        <p className="text-xs text-text-secondary mt-3 line-clamp-2">{reasoning}</p>
      )}

      {factors && factors.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {factors.slice(0, 4).map((f, i) => (
            <span key={i} className="text-[10px] px-1.5 py-0.5 rounded bg-bg text-text-secondary">
              {f}
            </span>
          ))}
        </div>
      )}
    </Card>
  )
}
