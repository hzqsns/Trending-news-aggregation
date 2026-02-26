import { useEffect, useState } from 'react'
import { CheckCircle, Shield } from 'lucide-react'
import { alertsApi } from '@/api'

interface Alert {
  id: number
  level: string
  title: string
  description: string
  skill_name: string | null
  suggestion: string | null
  is_active: boolean
  created_at: string
  resolved_at: string | null
}

const levelConfig: Record<string, { label: string; emoji: string; color: string; bg: string }> = {
  critical: { label: '紧急', emoji: '🚨', color: 'text-danger', bg: 'bg-danger/10' },
  high: { label: '高', emoji: '⚠️', color: 'text-warning', bg: 'bg-warning/10' },
  medium: { label: '中', emoji: '📢', color: 'text-primary', bg: 'bg-primary/10' },
  low: { label: '低', emoji: 'ℹ️', color: 'text-text-secondary', bg: 'bg-bg' },
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [showResolved, setShowResolved] = useState(false)

  const load = async () => {
    try {
      const resp = showResolved
        ? await alertsApi.list()
        : await alertsApi.active()
      setAlerts(resp.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [showResolved])

  const handleResolve = async (id: number) => {
    try {
      await alertsApi.resolve(id)
      load()
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">预警中心</h2>
        <label className="flex items-center gap-2 text-sm cursor-pointer">
          <input
            type="checkbox"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="rounded border-border"
          />
          显示已解除
        </label>
      </div>

      {loading ? (
        <div className="p-8 text-center text-text-secondary">加载中...</div>
      ) : alerts.length === 0 ? (
        <div className="bg-card rounded-xl p-12 text-center border border-border">
          <Shield size={48} className="mx-auto text-success/30 mb-4" />
          <p className="text-text-secondary">暂无活跃预警</p>
          <p className="text-xs text-text-secondary mt-1">系统正在持续监控市场动态</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => {
            const cfg = levelConfig[alert.level] || levelConfig.low
            return (
              <div key={alert.id} className={`bg-card rounded-xl border border-border p-5 ${!alert.is_active ? 'opacity-60' : ''}`}>
                <div className="flex items-start gap-3">
                  <span className={`shrink-0 w-10 h-10 flex items-center justify-center rounded-lg text-lg ${cfg.bg}`}>
                    {cfg.emoji}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg.bg} ${cfg.color}`}>
                        {cfg.label}
                      </span>
                      {!alert.is_active && (
                        <span className="text-xs text-success flex items-center gap-1">
                          <CheckCircle size={12} /> 已解除
                        </span>
                      )}
                      <span className="text-xs text-text-secondary ml-auto">
                        {new Date(alert.created_at).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    <h3 className="font-semibold text-sm">{alert.title}</h3>
                    <p className="text-sm text-text-secondary mt-1 whitespace-pre-line">{alert.description}</p>
                    {alert.suggestion && (
                      <div className="mt-2 p-3 bg-bg rounded-lg">
                        <p className="text-xs font-medium mb-1">💡 建议</p>
                        <p className="text-sm">{alert.suggestion}</p>
                      </div>
                    )}
                    {alert.is_active && (
                      <button
                        onClick={() => handleResolve(alert.id)}
                        className="mt-3 text-xs text-primary hover:underline"
                      >
                        标记为已解除
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
