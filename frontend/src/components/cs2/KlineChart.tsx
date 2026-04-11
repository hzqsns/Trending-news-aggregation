import { ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'

interface Point {
  time: string
  price: number
  volume: number
}

interface Props {
  data: Point[]
}

export function KlineChart({ data }: Props) {
  const chartData = data.map((p) => ({
    time: new Date(p.time).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }),
    price: p.price,
    volume: p.volume,
  }))

  if (chartData.length === 0) {
    return (
      <div className="h-[300px] flex items-center justify-center text-text-secondary text-sm">
        暂无价格历史数据
      </div>
    )
  }

  return (
    <div className="h-[300px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.1)" />
          <XAxis dataKey="time" tick={{ fontSize: 11 }} stroke="#888" />
          <YAxis yAxisId="price" orientation="right" tick={{ fontSize: 11 }} stroke="#888" />
          <YAxis yAxisId="volume" orientation="left" tick={{ fontSize: 11 }} stroke="#888" />
          <Tooltip
            contentStyle={{ backgroundColor: 'var(--color-card, #1a1a1a)', border: '1px solid rgba(128,128,128,0.2)', fontSize: '12px' }}
          />
          <Bar yAxisId="volume" dataKey="volume" fill="rgba(217, 119, 6, 0.3)" />
          <Line yAxisId="price" type="monotone" dataKey="price" stroke="#d97706" strokeWidth={2} dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
