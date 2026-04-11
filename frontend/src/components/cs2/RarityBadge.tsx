import { cn } from '@/lib/utils'

const RARITY_COLORS: Record<string, string> = {
  consumer: 'bg-gray-500/20 text-gray-400 border-gray-500/40',
  industrial: 'bg-sky-500/20 text-sky-400 border-sky-500/40',
  'mil-spec': 'bg-blue-600/20 text-blue-400 border-blue-600/40',
  restricted: 'bg-purple-600/20 text-purple-400 border-purple-600/40',
  classified: 'bg-pink-600/20 text-pink-400 border-pink-600/40',
  covert: 'bg-red-600/20 text-red-400 border-red-600/40',
  contraband: 'bg-amber-500/20 text-amber-400 border-amber-500/40',
}

const RARITY_LABELS: Record<string, string> = {
  consumer: '消费级',
  industrial: '工业级',
  'mil-spec': '军规级',
  restricted: '受限',
  classified: '保密',
  covert: '隐秘',
  contraband: '违禁',
}

interface Props {
  rarity: string | null
  className?: string
}

export function RarityBadge({ rarity, className }: Props) {
  if (!rarity) return null
  const color = RARITY_COLORS[rarity] ?? 'bg-gray-500/20 text-gray-400 border-gray-500/40'
  const label = RARITY_LABELS[rarity] ?? rarity
  return (
    <span
      className={cn(
        'inline-flex items-center text-[10px] px-1.5 py-0.5 rounded border font-medium',
        color,
        className,
      )}
    >
      {label}
    </span>
  )
}
