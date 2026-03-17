import { useEffect, useState } from 'react'
import { Save, Check, Eye, EyeOff, Zap, X } from 'lucide-react'
import { settingsApi } from '@/api'

interface SettingItem {
  id: number
  key: string
  value: string | null
  category: string
  label: string | null
  description: string | null
  field_type: string
  has_value?: boolean
}

const categoryInfo: Record<string, { label: string; icon: string }> = {
  system: { label: '系统配置', icon: '⚙️' },
  ai: { label: 'AI 配置', icon: '🤖' },
  sources: { label: '数据源配置', icon: '📡' },
  notifications: { label: '推送渠道', icon: '📮' },
  push_strategy: { label: '推送策略', icon: '📋' },
  twitter: { label: '推特追踪', icon: '🐦' },
}

interface AiProvider {
  key: string
  api_base: string
  default_model: string
}

export default function Settings() {
  const [grouped, setGrouped] = useState<Record<string, SettingItem[]>>({})
  const [edits, setEdits] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('system')
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})
  const [aiProviders, setAiProviders] = useState<AiProvider[]>([])
  const [testingAi, setTestingAi] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const load = async () => {
    try {
      const resp = await settingsApi.list()
      setGrouped(resp.data)
      const initial: Record<string, string> = {}
      for (const items of Object.values(resp.data) as SettingItem[][]) {
        for (const item of items) {
          initial[item.key] = item.value ?? ''
        }
      }
      setEdits(initial)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    settingsApi.aiProviders().then((r) => setAiProviders(r.data.providers)).catch(() => {})
  }, [])

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message })
    setTimeout(() => setToast(null), 3000)
  }

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const changed: Record<string, string> = {}
      for (const [key, value] of Object.entries(edits)) {
        if (value !== '••••••••') {
          changed[key] = value
        }
      }
      await settingsApi.batchUpdate(changed)
      setSaved(true)
      showToast('success', '设置已保存成功')
      setTimeout(() => setSaved(false), 3000)
      await load()
    } catch (e) {
      console.error(e)
      showToast('error', '保存失败，请重试')
    } finally {
      setSaving(false)
    }
  }

  const handleTestAi = async () => {
    setTestingAi(true)
    setTestResult(null)
    try {
      const resp = await settingsApi.testAi()
      setTestResult(resp.data)
    } catch (e) {
      setTestResult({ success: false, message: '请求失败，请检查网络连接' })
    } finally {
      setTestingAi(false)
    }
  }

  const handleProviderChange = (provider: string) => {
    setEdits((e) => ({ ...e, ai_provider: provider }))
    const preset = aiProviders.find((p) => p.key === provider)
    if (preset && preset.key !== 'custom') {
      setEdits((e) => ({
        ...e,
        ai_provider: provider,
        ai_api_base: preset.api_base,
        ai_model: preset.default_model,
      }))
    }
  }

  const tabs = Object.keys(categoryInfo)

  if (loading) {
    return <div className="p-8 text-center text-text-secondary">加载中...</div>
  }

  const currentItems = grouped[activeTab] || []

  return (
    <div>
      {/* Toast 通知 */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 flex items-center gap-2 px-4 py-3 rounded-lg shadow-lg text-white text-sm transition-all ${
          toast.type === 'success' ? 'bg-success' : 'bg-danger'
        }`}>
          {toast.type === 'success' ? <Check size={16} /> : <X size={16} />}
          {toast.message}
        </div>
      )}

      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold">系统设置</h2>
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-1.5 px-4 py-2 bg-primary hover:bg-primary-dark text-white rounded-lg text-sm transition-colors disabled:opacity-50"
        >
          {saved ? <><Check size={16} /> 已保存</> : <><Save size={16} /> {saving ? '保存中...' : '保存设置'}</>}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-card rounded-xl p-1 border border-border overflow-x-auto">
        {tabs.map((tab) => {
          const info = categoryInfo[tab]
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${
                activeTab === tab ? 'bg-primary text-white' : 'hover:bg-bg text-text-secondary'
              }`}
            >
              <span>{info.icon}</span>
              {info.label}
            </button>
          )
        })}
      </div>

      {/* Settings Form */}
      <div className="bg-card rounded-xl border border-border">
        <div className="p-5 border-b border-border">
          <h3 className="font-semibold">{categoryInfo[activeTab]?.icon} {categoryInfo[activeTab]?.label}</h3>
        </div>
        <div className="divide-y divide-border">
          {currentItems.map((item) => (
            <div key={item.key} className="p-5">
              <div className="flex flex-col sm:flex-row sm:items-start gap-4">
                <div className="sm:w-1/3">
                  <label className="text-sm font-medium">{item.label || item.key}</label>
                  {item.description && (
                    <p className="text-xs text-text-secondary mt-0.5">{item.description}</p>
                  )}
                </div>
                <div className="sm:w-2/3">
                  {item.key === 'ai_provider' && aiProviders.length > 0 ? (
                    <select
                      value={edits[item.key] ?? 'custom'}
                      onChange={(e) => handleProviderChange(e.target.value)}
                      className="w-full max-w-md px-3 py-2 rounded-lg border border-border text-sm"
                    >
                      {aiProviders.map((p) => (
                        <option key={p.key} value={p.key}>
                          {p.key === 'custom' ? '自定义' :
                           p.key === 'gemini' ? 'Google Gemini' :
                           p.key === 'openrouter' ? 'OpenRouter' :
                           p.key === 'dashscope' ? '阿里云 DashScope（通义千问）' :
                           p.key === 'deepseek' ? 'DeepSeek' :
                           p.key === 'openai' ? 'OpenAI' : p.key}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <SettingField
                      item={item}
                      value={edits[item.key] ?? ''}
                      onChange={(v) => setEdits((e) => ({ ...e, [item.key]: v }))}
                      showPassword={showPasswords[item.key] || false}
                      onTogglePassword={() =>
                        setShowPasswords((s) => ({ ...s, [item.key]: !s[item.key] }))
                      }
                    />
                  )}
                </div>
              </div>
            </div>
          ))}
          {currentItems.length === 0 && (
            <div className="p-8 text-center text-text-secondary">此分类暂无设置项</div>
          )}
        </div>

        {/* AI 配置测试按钮 */}
        {activeTab === 'ai' && (
          <div className="p-5 border-t border-border">
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestAi}
                disabled={testingAi}
                className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                <Zap size={16} />
                {testingAi ? '测试中...' : '测试 API 连接'}
              </button>
              {testResult && (
                <span className={`text-sm ${testResult.success ? 'text-success' : 'text-danger'}`}>
                  {testResult.success ? <Check size={14} className="inline mr-1" /> : <X size={14} className="inline mr-1" />}
                  {testResult.message}
                </span>
              )}
            </div>
            <p className="text-xs text-text-secondary mt-2">
              点击测试当前保存的 AI 配置是否能正常连接。请先保存设置再测试。
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

function SettingField({
  item,
  value,
  onChange,
  showPassword,
  onTogglePassword,
}: {
  item: SettingItem
  value: string
  onChange: (v: string) => void
  showPassword: boolean
  onTogglePassword: () => void
}) {
  switch (item.field_type) {
    case 'boolean':
      return (
        <button
          type="button"
          onClick={() => onChange(value === 'true' ? 'false' : 'true')}
          className={`relative w-12 h-6 rounded-full transition-colors ${value === 'true' ? 'bg-success' : 'bg-gray-300'}`}
        >
          <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform ${value === 'true' ? 'left-6' : 'left-0.5'}`} />
        </button>
      )
    case 'number':
      return (
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full max-w-xs px-3 py-2 rounded-lg border border-border text-sm"
        />
      )
    case 'password':
      return (
        <div className="relative max-w-md">
          <input
            type={showPassword ? 'text' : 'password'}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={item.has_value ? '已设置（留空不修改）' : '未设置'}
            className="w-full px-3 py-2 pr-10 rounded-lg border border-border text-sm"
          />
          <button
            type="button"
            onClick={onTogglePassword}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-text"
          >
            {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
      )
    case 'json':
      return (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          className="w-full px-3 py-2 rounded-lg border border-border text-sm font-mono"
          placeholder="JSON 格式"
        />
      )
    default:
      return (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full max-w-md px-3 py-2 rounded-lg border border-border text-sm"
        />
      )
  }
}
