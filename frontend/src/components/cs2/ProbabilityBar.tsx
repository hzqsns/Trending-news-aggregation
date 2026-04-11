interface Props {
  up: number
  flat: number
  down: number
}

export function ProbabilityBar({ up, flat, down }: Props) {
  const total = up + flat + down || 1
  const upPct = (up / total) * 100
  const flatPct = (flat / total) * 100
  const downPct = (down / total) * 100

  return (
    <div className="space-y-1">
      <div className="flex h-2 rounded-full overflow-hidden bg-bg">
        <div className="bg-green-500" style={{ width: `${upPct}%` }} />
        <div className="bg-gray-500" style={{ width: `${flatPct}%` }} />
        <div className="bg-red-500" style={{ width: `${downPct}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-text-secondary">
        <span className="text-green-500">↑ {upPct.toFixed(0)}%</span>
        <span>→ {flatPct.toFixed(0)}%</span>
        <span className="text-red-500">↓ {downPct.toFixed(0)}%</span>
      </div>
    </div>
  )
}
