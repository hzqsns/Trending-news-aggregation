import { Card } from '@/components/ui'
import type { LucideIcon } from 'lucide-react'

interface Props {
  label: string
  value: string | number
  change?: number
  icon: LucideIcon
  iconColor?: string
}

export function MarketStatCard({ label, value, change, icon: Icon, iconColor = 'text-amber-500' }: Props) {
  return (
    <Card>
      <div className="flex items-center gap-3 mb-2">
        <Icon size={20} className={iconColor} />
        <span className="text-sm text-text-secondary">{label}</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold">{value}</span>
        {change !== undefined && (
          <span className={`text-xs ${change >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {change >= 0 ? '+' : ''}{change.toFixed(2)}%
          </span>
        )}
      </div>
    </Card>
  )
}
